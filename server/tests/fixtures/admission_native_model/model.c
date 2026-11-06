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
static void reenter(void);
static int model_clock(clockid_t id, struct timespec *t) {
    (void)id;
    ++sample;
    if (sample == reenter_clock) reenter();
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
    puts("20 causal model scenarios passed; no native Mach calls");
    return 0;
}
