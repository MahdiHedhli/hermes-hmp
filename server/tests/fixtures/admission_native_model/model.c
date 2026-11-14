/* Causal model: no Mach kernel calls, IPC, subprocesses or native probes. */
#include <assert.h>
#include <mach/mach.h>
#include <stdbool.h>
#include <stdio.h>
#include <time.h>
#include <sys/types.h>
#include <unistd.h>

static int sample, reenter_clock, reenter_native, fail_native, native_calls;
static int receive_count, send_count;
static unsigned long long fake_now = 1000000000;
static void *active;
static int receive_mode, receive_calls;
static int retire_mode, reply_calls, retire_native_reentry, expire_clock;
static void reenter(void);
static int model_clock(clockid_t id, struct timespec *t) {
    (void)id;
    ++sample;
    if (sample == reenter_clock) reenter();
    if (sample == expire_clock) fake_now += 201;
    t->tv_sec = (time_t)(fake_now / 1000000000);
    t->tv_nsec = (long)(fake_now % 1000000000);
    return 0;
}
#define geteuid() ((uid_t)501)
#define getuid() ((uid_t)501)
#define clock_gettime model_clock
#include "hmp_admission_owner.c"
#undef clock_gettime

static void reenter(void) {
    assert(!hmp_admission_owner_close(active));
}
mach_port_t mach_task_self(void) { return 7; }
kern_return_t mach_port_allocate(mach_port_t task, int kind, mach_port_t *p) {
    assert(task == 7 && kind == MACH_PORT_RIGHT_RECEIVE);
    ++native_calls;
    if (fail_native == native_calls) return 5;
    *p = 91;
    ++receive_count;
    if (reenter_native == native_calls) reenter();
    return KERN_SUCCESS;
}
kern_return_t mach_port_insert_right(mach_port_t t, mach_port_t p, mach_port_t q, int type) {
    assert(t == 7 && p == 91 && q == 91 && type == MACH_MSG_TYPE_MAKE_SEND);
    ++native_calls;
    if (fail_native == native_calls) return 5;
    ++send_count;
    if (reenter_native == native_calls) reenter();
    return KERN_SUCCESS;
}
kern_return_t mach_port_mod_refs(mach_port_t t, mach_port_t p, int kind, int delta) {
    if (p == 92) {
        assert(t == 7 && kind == MACH_PORT_RIGHT_DEAD_NAME && delta == -1);
        ++reply_calls;
        if (retire_mode == 8 || retire_mode == 9) return 5;
        if (retire_native_reentry == reply_calls) reenter();
        return KERN_SUCCESS;
    }
    assert(t == 7 && p == 91 && kind == MACH_PORT_RIGHT_RECEIVE && delta == -1);
    ++native_calls;
    if (fail_native == native_calls) return 5;
    --receive_count;
    if (reenter_native == native_calls) reenter();
    return KERN_SUCCESS;
}
kern_return_t mach_port_deallocate(mach_port_t t, mach_port_t p) {
    assert(t == 7 && p == 91);
    ++native_calls;
    if (fail_native == native_calls) return 5;
    --send_count;
    if (reenter_native == native_calls) reenter();
    return KERN_SUCCESS;
}

kern_return_t mach_port_type(mach_port_t t, mach_port_t p, mach_port_type_t *type) {
    assert(t == 7 && p == 92);
    ++reply_calls;
    if (retire_mode == 6) return 5;
    *type = retire_mode == 2 ? MACH_PORT_TYPE_SEND_ONCE :
        (retire_mode == 3 ? 0 : MACH_PORT_TYPE_DEAD_NAME);
    if (retire_native_reentry == reply_calls) reenter();
    return KERN_SUCCESS;
}
kern_return_t mach_port_get_refs(mach_port_t t, mach_port_t p, int kind,
                                 mach_port_urefs_t *refs) {
    assert(t == 7 && p == 92 && kind == MACH_PORT_RIGHT_DEAD_NAME);
    ++reply_calls;
    if (retire_mode == 7) return 5;
    *refs = retire_mode == 4 ? 0 : (retire_mode == 5 ? 2 : 1);
    if (retire_native_reentry == reply_calls) reenter();
    return KERN_SUCCESS;
}

pid_t audit_token_to_pid(audit_token_t token) { return (pid_t)token.val[0]; }
uid_t audit_token_to_euid(audit_token_t token) { return (uid_t)token.val[1]; }
int audit_token_to_pidversion(audit_token_t token) { return (int)token.val[2]; }
kern_return_t mach_msg(mach_msg_header_t *header, mach_msg_option_t opts,
                      mach_msg_size_t send_size, mach_msg_size_t receive_size,
                      mach_port_t endpoint, mach_msg_timeout_t timeout, mach_port_t notify) {
    assert(receive_mode > 0 && endpoint == 91 && send_size == 0 && notify == 0);
    assert(opts == (MACH_RCV_MSG | MACH_RCV_TIMEOUT));
    assert(receive_size >= 64 + sizeof(mach_msg_audit_trailer_t) && timeout > 0);
    ++receive_calls;
    if (receive_mode == 2) return MACH_RCV_TIMED_OUT;
    if (receive_mode == 3) return 0x10004004; /* unknown copyout outcome */
    struct hmp_initial_request request = {0};
    request.header.msgh_bits = MACH_MSGH_BITS(18, 17);
    request.header.msgh_size = sizeof(request);
    request.header.msgh_local_port = 91;
    request.header.msgh_remote_port = 92;
    request.header.msgh_id = HMP_REQUEST_ID;
    request.schema = request.phase = 1;
    struct mach_trailer_model { mach_msg_audit_trailer_t value; } trailer = {0};
    trailer.value.msgh_trailer_size = sizeof(trailer.value);
    trailer.value.msgh_audit.val[0] = (uint32_t)getpid() + 100;
    trailer.value.msgh_audit.val[1] = 501;
    trailer.value.msgh_audit.val[2] = 5;
    if (receive_mode == 4) request.header.msgh_bits = MACH_MSGH_BITS(17, 17);
    if (receive_mode == 5) request.header.msgh_bits |= 0x80000000;
    if (receive_mode == 6) request.header.msgh_size = 1024;
    if (receive_mode == 7) trailer.value.msgh_trailer_size = 0;
    if (receive_mode == 8) request.reserved[0] = 1;
    if (receive_mode == 9) trailer.value.msgh_audit.val[1] = 502;
    if (receive_mode == 10) trailer.value.msgh_audit.val[0] = (uint32_t)getpid();
    if (receive_mode == 13) request.header.msgh_remote_port = MACH_PORT_NULL;
    if (receive_mode == 14) request.header.msgh_local_port = 90;
    if (receive_mode == 15) request.header.msgh_voucher_port = 93;
    if (receive_mode == 16) request.header.msgh_id = 0;
    if (receive_mode == 17) request.schema = 2;
    if (receive_mode == 18) request.phase = 2;
    if (receive_mode == 19) trailer.value.msgh_trailer_type = 1;
    if (receive_mode == 20) trailer.value.msgh_audit.val[2] = UINT32_MAX;
    if (receive_mode == 21) trailer.value.msgh_audit.val[1] = 0;
    if (receive_mode == 22) trailer.value.msgh_audit.val[0] = 1;
    if (receive_mode == 23) trailer.value.msgh_trailer_size += 4;
    if (receive_mode == 24) request.header.msgh_bits |= 0x10000000;
    memcpy(header, &request, sizeof(request));
    memcpy((unsigned char *)header + sizeof(request), &trailer.value, sizeof(trailer.value));
    if (receive_mode == 11) fake_now += 201;
    if (receive_mode == 12) reenter();
    return MACH_MSG_SUCCESS;
}

int main(void) {
    /* Ordinary known closure and disposal. */
    hmp_admission_owner *o = hmp_admission_owner_allocate();
    assert(o); active = o;
    assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
    assert(hmp_admission_owner_state(o) == HMP_ADMISSION_ENDPOINT);
    assert(hmp_admission_owner_close(o));
    assert(hmp_admission_owner_close(o));
    assert(receive_count == 0 && send_count == 0 && native_calls == 4);
    assert(hmp_admission_owner_dispose(&o) && o == NULL);

    /* Each native boundary: returned resources are retained BEFORE refusal.
     * No later effect, retry, state revival or disposal after reentry. */
    for (int boundary = 1; boundary <= 4; ++boundary) {
        sample = native_calls = receive_count = send_count = 0;
        reenter_native = boundary;
        o = hmp_admission_owner_allocate(); active = o;
        bool initialized = hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200);
        if (boundary <= 2) assert(!initialized); else assert(initialized);
        assert(!hmp_admission_owner_close(o));
        assert(o->integrity_refused && o->state == HMP_ADMISSION_REFUSED);
        assert(native_calls == boundary);
        assert(o->receive_owned == (receive_count == 1));
        assert(o->send_owned == (send_count == 1));
        assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
        assert(native_calls == boundary);
        /* Model allocations deliberately remain retained until this test exits. */
    }
    reenter_native = 0;

    /* Every clock sample in initialize/close: reentry prevents the NEXT effect
     * and final CLOSED publication; first close-clock regression is included. */
    for (int boundary = 1; boundary <= 6; ++boundary) {
        sample = native_calls = receive_count = send_count = 0;
        reenter_clock = boundary;
        o = hmp_admission_owner_allocate(); active = o;
        bool initialized = hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200);
        if (boundary <= 3) assert(!initialized); else assert(initialized);
        assert(!hmp_admission_owner_close(o));
        assert(o->integrity_refused && o->state == HMP_ADMISSION_REFUSED);
        const int expected_calls[] = {0, 1, 2, 2, 3, 4};
        assert(native_calls == expected_calls[boundary - 1]);
        int before = native_calls;
        assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
        assert(native_calls == before);
    }
    reenter_clock = 0;

    /* Native failures: initialization partial ownership can close; release
     * uncertainty is sticky and never replayed. */
    for (int boundary = 1; boundary <= 4; ++boundary) {
        sample = native_calls = receive_count = send_count = 0;
        fail_native = boundary;
        o = hmp_admission_owner_allocate(); active = o;
        bool initialized = hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200);
        if (boundary <= 2) {
            assert(!initialized && hmp_admission_owner_close(o));
            assert(hmp_admission_owner_dispose(&o));
        } else {
            assert(initialized && !hmp_admission_owner_close(o));
            int before = native_calls;
            assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
            assert(native_calls == before && o->uncertain);
        }
    }
    fail_native = 0;

    /* Expired cleanup retains both rights without issuing a release. */
    sample = native_calls = receive_count = send_count = 0;
    o = hmp_admission_owner_allocate(); active = o;
    assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
    fake_now += 201;
    assert(!hmp_admission_owner_close(o));
    assert(native_calls == 2 && o->receive_owned && o->send_owned);
    assert(!hmp_admission_owner_dispose(&o));
    /* Wrong process cannot use or free the original retained resource owner. */
    sample = native_calls = receive_count = send_count = 0;
    o = hmp_admission_owner_allocate();
    o->process += 1;
    assert(!hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
    assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
    assert(native_calls == 0);

    /* Bad original deadlines never allocate rights, but allow empty disposal. */
    for (int bad = 0; bad < 3; ++bad) {
        o = hmp_admission_owner_allocate();
        uint64_t end = bad == 0 ? fake_now : fake_now + 100;
        uint64_t cleanup = bad == 1 ? fake_now + 50 :
            (bad == 2 ? fake_now + 20000000001ULL : fake_now + 200);
        assert(!hmp_admission_owner_initialize(o, end, cleanup));
        assert(native_calls == 0 && hmp_admission_owner_close(o));
        assert(hmp_admission_owner_dispose(&o));
    }
    /* One receive cursor; success and invalid/late/reentrant output retain the
     * full message/reply. No close, destructor or send is permitted afterwards. */
    for (int mode = 1; mode <= 24; ++mode) {
        receive_mode = mode;
        receive_calls = sample = native_calls = receive_count = send_count = 0;
        o = hmp_admission_owner_allocate(); active = o;
        assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
        bool observed = hmp_admission_owner_observe_request(o);
        assert(observed == (mode == 1));
        assert(receive_calls == 1 && native_calls == 2);
        if (mode == 1) assert(o->state == HMP_ADMISSION_REQUEST_OBSERVED);
        assert(!hmp_admission_owner_observe_request(o));
        assert(receive_calls == 1 && native_calls == 2);
        if (mode != 2 && mode != 3) {
            assert(o->request_received && o->request_reply == (mode == 13 ? 0u : 92u));
            assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
            assert(native_calls == 2);
        } else if (mode == 3) {
            assert(o->request_copyout_unknown && o->uncertain);
            assert(!hmp_admission_owner_close(o) && native_calls == 2);
        } else {
            assert(!o->request_received && !o->request_copyout_unknown);
            assert(hmp_admission_owner_close(o) && hmp_admission_owner_dispose(&o));
        }
        if (o != NULL) assert(!hmp_admission_owner_observe_request(o));
        assert(receive_calls == 1);
    }
    /* Three request clock boundaries: before receive, after ownership capture,
     * and before publishing the observation. No next effect or late success. */
    for (int boundary = 4; boundary <= 6; ++boundary) {
        receive_mode = 1;
        reenter_clock = boundary;
        sample = native_calls = receive_count = send_count = receive_calls = 0;
        o = hmp_admission_owner_allocate(); active = o;
        assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
        assert(!hmp_admission_owner_observe_request(o));
        int expected = boundary == 4 ? 0 : 1;
        assert(receive_calls == expected && native_calls == 2);
        assert(o->request_received == (expected == 1));
        if (expected == 1) assert(o->request_reply == 92);
        assert(o->integrity_refused && o->state == HMP_ADMISSION_REFUSED);
        assert(!hmp_admission_owner_observe_request(o));
        assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
        assert(receive_calls == expected && native_calls == 2);
    }
    reenter_clock = 0;
    /* Typed DEAD_NAME retirement: live or malformed/uncertain rights do not
     * enter a polymorphic destructor; body refusal does not invent extra rights. */
    for (int mode = 1; mode <= 12; ++mode) {
        retire_mode = mode;
        receive_mode = mode == 10 ? 5 : (mode == 11 ? 3 : (mode == 12 ? 8 : 1));
        reply_calls = sample = native_calls = receive_count = send_count = receive_calls = 0;
        o = hmp_admission_owner_allocate(); active = o;
        assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
        bool observed = hmp_admission_owner_observe_request(o);
        assert(observed == (mode < 10));
        bool retired = hmp_admission_owner_retire_dead_reply(o);
        assert(retired == (mode == 1 || mode == 12));
        int expected = mode >= 10 && mode <= 11 ? 0 :
            (mode == 2 || mode == 3 || mode == 6 ? 1 :
             (mode == 4 || mode == 5 || mode == 7 ? 2 : 3));
        assert(reply_calls == expected);
        assert(!hmp_admission_owner_retire_dead_reply(o) && reply_calls == expected);
        if (retired) {
            assert(o->reply_released && o->reply_retired_timely && o->request_reply == 0);
            assert(hmp_admission_owner_close(o) && native_calls == 4);
            assert(hmp_admission_owner_dispose(&o));
        } else {
            assert(!o->reply_released && !o->reply_retired_timely);
            assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
            assert(native_calls == 2);
        }
    }
    retire_mode = 1;
    /* Reentry at each query/release return boundary. Returned release is
     * recorded even though timely retirement and subsequent cleanup refuse. */
    for (int boundary = 1; boundary <= 3; ++boundary) {
        retire_native_reentry = boundary;
        receive_mode = 1;
        reply_calls = sample = native_calls = receive_count = send_count = receive_calls = 0;
        o = hmp_admission_owner_allocate(); active = o;
        assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
        assert(hmp_admission_owner_observe_request(o));
        assert(!hmp_admission_owner_retire_dead_reply(o));
        assert(reply_calls == boundary && o->reply_released == (boundary == 3));
        assert(!o->reply_retired_timely && o->integrity_refused);
        assert(!hmp_admission_owner_retire_dead_reply(o));
        assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
        assert(reply_calls == boundary && native_calls == 2);
    }
    retire_native_reentry = 0;
    for (int kind = 0; kind < 2; ++kind) {
        for (int boundary = 1; boundary <= 4; ++boundary) {
            reenter_clock = expire_clock = 0;
            reply_calls = sample = native_calls = receive_count = send_count = receive_calls = 0;
            o = hmp_admission_owner_allocate(); active = o;
            assert(hmp_admission_owner_initialize(o, fake_now + 100, fake_now + 200));
            assert(hmp_admission_owner_observe_request(o));
            sample = 0;
            if (kind == 0) reenter_clock = boundary; else expire_clock = boundary;
            assert(!hmp_admission_owner_retire_dead_reply(o));
            assert(reply_calls == boundary - 1);
            assert(o->reply_released == (boundary == 4) && !o->reply_retired_timely);
            assert(!hmp_admission_owner_retire_dead_reply(o));
            assert(!hmp_admission_owner_close(o) && !hmp_admission_owner_dispose(&o));
            assert(reply_calls == boundary - 1 && native_calls == 2);
        }
    }
    puts("70 causal model scenarios passed; no native Mach calls");
    return 0;
}
