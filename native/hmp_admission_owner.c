/* Endpoint ownership only. This source is not loaded by HMP and supplies no
 * startup attestation, message receiver, handshake, right export or IO permit.
 */
#include "hmp_admission_owner.h"

#include <mach/mach.h>
#include <pthread.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

struct hmp_admission_owner {
    pid_t process;
    pthread_t thread;
    hmp_admission_state state;
    uint64_t work_end, cleanup_end;
    mach_port_t endpoint;
    bool initialize_attempted, close_attempted;
    bool receive_owned, send_owned, uncertain, busy, integrity_refused;
};

static uint64_t clock_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0 || t.tv_sec < 0 ||
        t.tv_nsec < 0 || t.tv_nsec >= 1000000000 ||
        (uint64_t)t.tv_sec > (UINT64_MAX - 999999999) / 1000000000) return UINT64_MAX;
    return (uint64_t)t.tv_sec * 1000000000 + (uint64_t)t.tv_nsec;
}

static bool original(hmp_admission_owner *o) {
    return o != NULL && o->process == getpid() && pthread_equal(o->thread, pthread_self());
}

static bool enter(hmp_admission_owner *o) {
    if (!original(o)) return false;
    if (o->busy) {
        o->integrity_refused = true;
        o->state = HMP_ADMISSION_REFUSED;
        return false;
    }
    o->busy = true;
    return true;
}

static bool leave(hmp_admission_owner *o, bool result) {
    o->busy = false;
    if (o->integrity_refused) o->state = HMP_ADMISSION_REFUSED;
    return result && !o->integrity_refused;
}

hmp_admission_owner *hmp_admission_owner_allocate(void) {
    hmp_admission_owner *o = calloc(1, sizeof(*o));
    if (o != NULL) {
        o->process = getpid();
        o->thread = pthread_self();
        o->state = HMP_ADMISSION_EMPTY;
        o->endpoint = MACH_PORT_NULL;
    }
    return o;
}

static bool initialize(hmp_admission_owner *o, uint64_t end,
                                    uint64_t cleanup_end) {
    if (!original(o)) return false;
    if (o->initialize_attempted || o->close_attempted || o->state != HMP_ADMISSION_EMPTY) {
        if (o->state != HMP_ADMISSION_CLOSED) o->state = HMP_ADMISSION_REFUSED;
        return false;
    }
    o->initialize_attempted = true;
    o->state = HMP_ADMISSION_REFUSED; /* All partial initialization is retained. */
    uint64_t now = clock_ns();
    if (geteuid() == 0 || geteuid() != getuid() || now == UINT64_MAX || end <= now ||
        cleanup_end < end || cleanup_end - now > 20000000000ULL || o->integrity_refused) return false;
    o->work_end = end;
    o->cleanup_end = cleanup_end;
    kern_return_t r = mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &o->endpoint);
    if (r != KERN_SUCCESS) {
        /* No output right is assumed on an unsuccessful allocate. */
        o->endpoint = MACH_PORT_NULL;
        return false;
    }
    o->receive_owned = true;
    if (clock_ns() >= o->work_end || o->integrity_refused) return false;
    r = mach_port_insert_right(mach_task_self(), o->endpoint, o->endpoint,
                              MACH_MSG_TYPE_MAKE_SEND);
    if (r != KERN_SUCCESS) return false;
    o->send_owned = true;
    if (clock_ns() >= o->work_end || o->integrity_refused) return false;
    o->state = HMP_ADMISSION_ENDPOINT;
    return true;
}

bool hmp_admission_owner_initialize(hmp_admission_owner *o, uint64_t end,
                                    uint64_t cleanup_end) {
    if (!enter(o)) return false;
    bool result = initialize(o, end, cleanup_end);
    return leave(o, result);
}

hmp_admission_state hmp_admission_owner_state(hmp_admission_owner *o) {
    if (!enter(o)) return HMP_ADMISSION_REFUSED;
    if (o->state == HMP_ADMISSION_ENDPOINT && clock_ns() >= o->work_end)
        o->state = HMP_ADMISSION_REFUSED;
    (void)leave(o, true);
    return o->state;
}

static bool close_owner(hmp_admission_owner *o) {
    if (!original(o)) return false;
    if (o->close_attempted) return o->state == HMP_ADMISSION_CLOSED;
    o->close_attempted = true;
    o->state = HMP_ADMISSION_REFUSED;
    /* Allocation has no Mach effects. Invalid initialization can still be
     * disposed if it created no rights; no invented cleanup budget is needed. */
    if (!o->receive_owned && !o->send_owned && !o->uncertain) {
        o->state = HMP_ADMISSION_CLOSED;
        return true;
    }
    if (clock_ns() >= o->cleanup_end || o->integrity_refused) return false;
    if (o->receive_owned) {
        kern_return_t r = mach_port_mod_refs(mach_task_self(), o->endpoint,
                                             MACH_PORT_RIGHT_RECEIVE, -1);
        if (r != KERN_SUCCESS) { o->uncertain = true; return false; }
        o->receive_owned = false;
    }
    if (clock_ns() >= o->cleanup_end || o->integrity_refused) return false;
    if (o->send_owned) {
        /* Destroying the receive right converts the own send reference to a
         * dead name. Deallocate exactly that retained reference, never retry. */
        kern_return_t r = mach_port_deallocate(mach_task_self(), o->endpoint);
        if (r != KERN_SUCCESS) { o->uncertain = true; return false; }
        o->send_owned = false;
    }
    if (clock_ns() >= o->cleanup_end || o->uncertain || o->integrity_refused) return false;
    o->endpoint = MACH_PORT_NULL;
    o->state = HMP_ADMISSION_CLOSED;
    return true;
}

bool hmp_admission_owner_close(hmp_admission_owner *o) {
    if (!enter(o)) return false;
    bool result = close_owner(o);
    return leave(o, result);
}

bool hmp_admission_owner_dispose(hmp_admission_owner **owner) {
    if (owner == NULL || !enter(*owner)) return false;
    hmp_admission_owner *o = *owner;
    if (o->state != HMP_ADMISSION_CLOSED || !o->close_attempted ||
        o->receive_owned || o->send_owned || o->uncertain || o->integrity_refused)
        return leave(o, false);
    *owner = NULL;
    free(o);
    return true;
}
