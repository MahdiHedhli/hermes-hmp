/* One isolated native lifecycle harness. Only own task Mach rights and one
 * joined thread; no messages, global names, services, children or user data. */
#include <mach/mach.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <time.h>
#include "hmp_admission_owner.h"

static bool dead_name_observed;
static kern_return_t observed_release(mach_port_t task, mach_port_t name,
                                      mach_port_right_t right, mach_port_delta_t delta) {
    kern_return_t result = mach_port_mod_refs(task, name, right, delta);
    if (result == KERN_SUCCESS && right == MACH_PORT_RIGHT_RECEIVE && delta == -1) {
        mach_port_type_t type = 0;
        mach_port_urefs_t refs = 0;
        dead_name_observed = mach_port_type(task, name, &type) == KERN_SUCCESS &&
            type == MACH_PORT_TYPE_DEAD_NAME &&
            mach_port_get_refs(task, name, MACH_PORT_RIGHT_DEAD_NAME, &refs) == KERN_SUCCESS &&
            refs == 1;
    }
    return result;
}
#define mach_port_mod_refs observed_release
#include "hmp_admission_owner.c"
#undef mach_port_mod_refs

struct wrong_thread {
    hmp_admission_owner *owner;
    bool refused;
};
static void *foreign(void *arg) {
    struct wrong_thread *test = arg;
    hmp_admission_owner *local = test->owner;
    test->refused = hmp_admission_owner_state(local) == HMP_ADMISSION_REFUSED &&
        !hmp_admission_owner_close(local) && !hmp_admission_owner_dispose(&local) &&
        local == test->owner;
    return NULL;
}

int main(void) {
    hmp_admission_owner *owner = hmp_admission_owner_allocate();
    if (owner == NULL) return 1;
    uint64_t start = clock_ns();
    bool initialized = start != UINT64_MAX && start <= UINT64_MAX - 8000000000ULL &&
        hmp_admission_owner_initialize(owner, start + 5000000000ULL, start + 8000000000ULL);
    bool own_rights = false, joined = false, thread_created = false;
    bool wrong_thread_refused = false;
    struct wrong_thread *test = calloc(1, sizeof(*test));
    mach_port_t original_port = MACH_PORT_NULL;
    if (initialized) {
        original_port = owner->endpoint;
        mach_port_urefs_t receive_refs = 0, send_refs = 0;
        own_rights = mach_port_get_refs(mach_task_self(), original_port,
            MACH_PORT_RIGHT_RECEIVE, &receive_refs) == KERN_SUCCESS && receive_refs == 1 &&
            mach_port_get_refs(mach_task_self(), original_port,
            MACH_PORT_RIGHT_SEND, &send_refs) == KERN_SUCCESS && send_refs == 1;
        pthread_t thread;
        if (test != NULL) test->owner = owner;
        if (test != NULL && pthread_create(&thread, NULL, foreign, test) == 0) {
            thread_created = true;
            joined = pthread_join(thread, NULL) == 0;
            if (joined) wrong_thread_refused = test->refused;
        }
    }
    /* A failed join cannot permit freeing data still visible to that thread.
     * Retain both allocations and all rights; report failure, never closure.
     * Process teardown is not represented as explicit timely cleanup. */
    bool thread_settled = !thread_created || joined;
    if (thread_settled) free(test);
    bool close_known = thread_settled && hmp_admission_owner_close(owner);
    bool idempotent_close = close_known && hmp_admission_owner_close(owner);
    mach_port_type_t after_type = 0;
    bool name_absent = close_known && original_port != MACH_PORT_NULL &&
        mach_port_type(mach_task_self(), original_port, &after_type) == KERN_INVALID_NAME;
    bool disposed = close_known && hmp_admission_owner_dispose(&owner) && owner == NULL;
    bool passed = initialized && own_rights && joined && wrong_thread_refused &&
        dead_name_observed && close_known && idempotent_close && name_absent && disposed;
    printf("{\"schema\":1,\"initialized\":%s,\"own_rights\":%s,"
        "\"thread_joined\":%s,\"wrong_thread_refused\":%s,\"dead_name_observed\":%s,"
        "\"close_known\":%s,\"idempotent_close\":%s,\"name_absent\":%s,"
        "\"disposed\":%s,\"production_qualified\":false}\n",
        initialized ? "true" : "false", own_rights ? "true" : "false",
        joined ? "true" : "false", wrong_thread_refused ? "true" : "false",
        dead_name_observed ? "true" : "false", close_known ? "true" : "false",
        idempotent_close ? "true" : "false", name_absent ? "true" : "false",
        disposed ? "true" : "false");
    return passed ? 0 : 1;
}
