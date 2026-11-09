"""Actual Store+actor CAS, not socket peer or human consent qualification."""
import asyncio
import time
from types import SimpleNamespace
import pytest
from hmp_plugin.store import Store
from hmp_plugin.media_publication_actor import MediaPublicationActor
from hmp_plugin.media_operator_protocol import MediaReadMutation
from hmp_plugin.media_operator_execution import (
    MediaOperatorExecutor, MediaMutationRefused, MediaMutationUnknown,
)


async def setup(tmp_path):
    actor = MediaPublicationActor()
    store = Store(tmp_path / 'store.sqlite3', mutation_observer=actor); store.migrate()
    await asyncio.to_thread(store.insert_user, 'user', 'owner', 1)
    await asyncio.to_thread(store.insert_device, 'device', 'user', 'f' * 52, b'public',
                            'phone', 1, state='ACTIVE')
    ctx = SimpleNamespace(iid='a' * 52, identity=SimpleNamespace(still_current=lambda: True),
                          store=store, bridge=object(), readiness_generation='b' * 32,
                          now=lambda: 2)
    expected = store.media_read_decision(ctx.iid, 'device')
    request = MediaReadMutation(ctx.iid, 'c' * 32, ctx.readiness_generation, 'd' * 32,
                               'device', expected, True)
    return actor, store, ctx, request


def test_real_operator_cas_and_duplicate_snapshot_never_replays_write(tmp_path):
    async def scenario():
        actor, store, ctx, request = await setup(tmp_path)
        executor = MediaOperatorExecutor(ctx, actor, 'c' * 32)
        result = await asyncio.to_thread(executor.decide, request, deadline=time.monotonic()+1.0)
        assert result.status == 'committed' and result.decision.allowed is True
        assert result.decision.revision == 1
        duplicate = await asyncio.to_thread(executor.decide, request, deadline=time.monotonic()+1.0)
        assert duplicate.status == 'conflict'
        assert store.media_read_decision(ctx.iid, 'device').revision == 1
        assert store.owner_controls_decision('device') is None
        assert repr(result) == '<MediaMutationResult redacted>'
        actor.close(); await actor.wait_drained(); store.close()
    asyncio.run(scenario())


@pytest.mark.parametrize('bad', ('nonce', 'generation', 'expired', 'loop'))
def test_refused_scope_or_deadline_starts_no_media_mutation(tmp_path, bad):
    async def scenario():
        actor, store, ctx, request = await setup(tmp_path)
        executor = MediaOperatorExecutor(ctx, actor, 'c' * 32)
        if bad in ('nonce', 'generation'):
            fields = {name: getattr(request, name) for name in request.__dataclass_fields__}
            fields[bad] = 'e' * 32; request = MediaReadMutation(**fields)
        deadline = time.monotonic() + (-1.0 if bad == 'expired' else 1.0)
        with pytest.raises(MediaMutationRefused):
            if bad == 'loop': executor.decide(request, deadline=deadline)
            else: await asyncio.to_thread(executor.decide, request, deadline=deadline)
        assert store.media_read_decision(ctx.iid, 'device').allowed is None
        assert actor.outstanding_mutations() == 0
        actor.close(); await actor.wait_drained(); store.close()
    asyncio.run(scenario())


def test_postcommit_readback_loss_remains_unknown_without_replay(tmp_path, monkeypatch):
    async def scenario():
        actor, store, ctx, request = await setup(tmp_path)
        def unavailable(*args): raise OSError('synthetic readback loss')
        monkeypatch.setattr(store, 'media_read_decision', unavailable)
        executor = MediaOperatorExecutor(ctx, actor, 'c' * 32)
        with pytest.raises(MediaMutationUnknown, match='inspect; do not replay'):
            await asyncio.to_thread(executor.decide, request, deadline=time.monotonic()+1.0)
        monkeypatch.undo()
        actual = store.media_read_decision(ctx.iid, 'device')
        assert actual.allowed is True and actual.revision == 1
        assert actor.outstanding_mutations() == 0
        actor.close(); await actor.wait_drained(); store.close()
    asyncio.run(scenario())


def test_context_drift_after_cas_rolls_back_and_never_claims_success(tmp_path):
    async def scenario():
        actor, store, ctx, request = await setup(tmp_path)
        checks = []
        def identity_current():
            checks.append(1)
            if len(checks) == 4: ctx.bridge = object()  # post-CAS, before COMMIT
            return True
        ctx.identity.still_current = identity_current
        executor = MediaOperatorExecutor(ctx, actor, 'c' * 32)
        with pytest.raises(MediaMutationUnknown):
            await asyncio.to_thread(executor.decide, request, deadline=time.monotonic()+1.0)
        assert len(checks) == 4
        actual = store.media_read_decision(ctx.iid, 'device')
        assert actual.allowed is None and actual.revision == 0
        assert actor.outstanding_mutations() == 0
        actor.close(); await actor.wait_drained(); store.close()
    asyncio.run(scenario())


def test_changed_actor_publisher_refuses_before_sql(tmp_path):
    from hmp_plugin.media_publication import MediaPublication
    async def scenario():
        actor, store, ctx, request = await setup(tmp_path)
        executor = MediaOperatorExecutor(ctx, actor, 'c' * 32)
        actor._publisher = MediaPublication()
        with pytest.raises(MediaMutationRefused):
            await asyncio.to_thread(executor.decide, request, deadline=time.monotonic()+1.0)
        assert store.media_read_decision(ctx.iid, 'device').allowed is None
        assert actor.outstanding_mutations() == 0
        actor.close(); await actor.wait_drained(); store.close()
    asyncio.run(scenario())
