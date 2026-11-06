/* Endpoint ownership only. This source is not loaded by HMP and supplies no
 * startup attestation, handshake, right export or IO permit. Request receipt is
 * observation-only with retained message debt; no production receiver admitted.
 */
#include "hmp_admission_owner.h"

#include <mach/mach.h>
#include <bsm/libbsm.h>
#include <string.h>
#include <pthread.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

enum { HMP_REQUEST_ID = 0x484d4101, HMP_REQUEST_LIMIT = 1024 };
struct hmp_initial_request {
    mach_msg_header_t header;
    uint32_t schema, phase;
    unsigned char reserved[32];
};
_Static_assert(sizeof(mach_msg_header_t) == 24, "Unsupported Mach header ABI");
_Static_assert(sizeof(struct hmp_initial_request) == 64, "Unexpected request padding");
_Static_assert(sizeof(mach_msg_audit_trailer_t) == 52, "Unsupported audit trailer ABI");

struct hmp_admission_owner {
    pid_t process;
    pthread_t thread;
    hmp_admission_state state;
    uint64_t work_end, cleanup_end;
    mach_port_t endpoint;
    bool initialize_attempted, close_attempted;
    bool receive_owned, send_owned, uncertain, busy, integrity_refused;
    bool request_attempted, request_received, request_copyout_unknown;
    bool request_simple_reply_only, reply_retirement_attempted;
    bool reply_released, reply_retired_timely;
    mach_port_t request_reply;
    pid_t observed_pid;
    uid_t observed_uid;
    int observed_pidversion;
    union {
        mach_msg_header_t alignment;
        unsigned char bytes[HMP_REQUEST_LIMIT + MAX_TRAILER_SIZE];
    } request_buffer;
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
    if ((o->state == HMP_ADMISSION_ENDPOINT || o->state == HMP_ADMISSION_REQUEST_OBSERVED)
        && clock_ns() >= o->work_end)
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
    /* Retained received rights must not be implicitly destroyed as endpoint
     * cleanup. In particular SEND_ONCE disposal may notify a foreign endpoint.
     * No generic message-disposal authority exists in this foundation yet. */
    if ((o->request_received && !(o->request_simple_reply_only && o->reply_released &&
        o->reply_retired_timely && o->request_reply == MACH_PORT_NULL)) ||
        o->request_copyout_unknown || o->uncertain) return false;
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
        o->receive_owned || o->send_owned || o->uncertain || o->integrity_refused ||
        (o->request_received && !o->reply_retired_timely))
        return leave(o, false);
    *owner = NULL;
    free(o);
    return true;
}

static bool observe_request(hmp_admission_owner *o) {
    if (o->state != HMP_ADMISSION_ENDPOINT || o->request_attempted ||
        o->close_attempted || o->integrity_refused) {
        o->state = HMP_ADMISSION_REFUSED;
        return false;
    }
    o->request_attempted = true;
    o->state = HMP_ADMISSION_REFUSED;
    uint64_t now = clock_ns();
    if (now >= o->work_end || o->integrity_refused) return false;
    uint64_t milliseconds = (o->work_end - now + 999999) / 1000000;
    /* One finite receive, no retry/cursor replacement; same original deadline. */
    mach_msg_timeout_t timeout = (mach_msg_timeout_t)(milliseconds > 1000 ? 1000 : milliseconds);
    mach_msg_header_t *header = (mach_msg_header_t *)o->request_buffer.bytes;
    kern_return_t r = mach_msg(header, MACH_RCV_MSG | MACH_RCV_TIMEOUT |
        MACH_RCV_TRAILER_TYPE(MACH_MSG_TRAILER_FORMAT_0) |
        MACH_RCV_TRAILER_ELEMENTS(MACH_RCV_TRAILER_AUDIT), 0,
        (mach_msg_size_t)sizeof(o->request_buffer), o->endpoint, timeout, MACH_PORT_NULL);
    if (r != MACH_MSG_SUCCESS) {
        if (r != MACH_RCV_TIMED_OUT) o->request_copyout_unknown = o->uncertain = true;
        return false;
    }
    /* Actual kernel output and its complete buffer belong to the owner BEFORE
     * clock/reentry/shape checks. No guessed destructor, release or send. */
    o->request_received = true;
    o->request_reply = header->msgh_remote_port;
    if (clock_ns() >= o->work_end || o->integrity_refused) return false;
    if (header->msgh_size != sizeof(struct hmp_initial_request) ||
        header->msgh_bits != MACH_MSGH_BITS(MACH_MSG_TYPE_PORT_SEND_ONCE, MACH_MSG_TYPE_PORT_SEND) ||
        header->msgh_local_port != o->endpoint || !MACH_PORT_VALID(o->request_reply) ||
        header->msgh_voucher_port != MACH_PORT_NULL || header->msgh_id != HMP_REQUEST_ID) return false;
    /* This is ownership shape, not admission: a later body/trailer refusal
     * still leaves only this one copied reply right, plus the borrowed local. */
    o->request_simple_reply_only = true;
    size_t offset = ((size_t)header->msgh_size + 3u) & ~(size_t)3u;
    if (offset > sizeof(o->request_buffer.bytes) - sizeof(mach_msg_audit_trailer_t)) return false;
    mach_msg_audit_trailer_t trailer;
    memcpy(&trailer, o->request_buffer.bytes + offset, sizeof(trailer));
    if (trailer.msgh_trailer_type != MACH_MSG_TRAILER_FORMAT_0 ||
        trailer.msgh_trailer_size != sizeof(trailer)) return false;
    struct hmp_initial_request request;
    memcpy(&request, header, sizeof(request));
    if (request.schema != 1 || request.phase != 1) return false;
    for (size_t i = 0; i < sizeof(request.reserved); ++i)
        if (request.reserved[i] != 0) return false;
    pid_t pid = audit_token_to_pid(trailer.msgh_audit);
    uid_t uid = audit_token_to_euid(trailer.msgh_audit);
    int version = audit_token_to_pidversion(trailer.msgh_audit);
    if (pid <= 1 || pid == o->process || uid == 0 || uid != geteuid() || version < 0 ||
        clock_ns() >= o->work_end || o->integrity_refused) return false;
    o->observed_pid = pid;
    o->observed_uid = uid;
    o->observed_pidversion = version;
    o->state = HMP_ADMISSION_REQUEST_OBSERVED;
    return true;
}

bool hmp_admission_owner_observe_request(hmp_admission_owner *o) {
    if (!enter(o)) return false;
    bool result = observe_request(o);
    return leave(o, result);
}

static bool retire_dead_reply(hmp_admission_owner *o) {
    if (o->reply_retirement_attempted || o->close_attempted) {
        o->state = HMP_ADMISSION_REFUSED;
        return false;
    }
    o->reply_retirement_attempted = true;
    o->state = HMP_ADMISSION_REFUSED;
    if (!o->request_received || !o->request_simple_reply_only || o->request_copyout_unknown ||
        o->uncertain || o->integrity_refused || !MACH_PORT_VALID(o->request_reply)) return false;
    const mach_port_t held_reply = o->request_reply;
    if (clock_ns() >= o->cleanup_end || o->integrity_refused) return false;
    mach_port_type_t type = 0;
    kern_return_t r = mach_port_type(mach_task_self(), held_reply, &type);
    if (r != KERN_SUCCESS) { o->uncertain = true; return false; }
    if (clock_ns() >= o->cleanup_end || o->integrity_refused ||
        o->request_reply != held_reply || type != MACH_PORT_TYPE_DEAD_NAME) return false;
    mach_port_urefs_t refs = 0;
    r = mach_port_get_refs(mach_task_self(), held_reply, MACH_PORT_RIGHT_DEAD_NAME, &refs);
    if (r != KERN_SUCCESS) { o->uncertain = true; return false; }
    if (clock_ns() >= o->cleanup_end || o->integrity_refused ||
        o->request_reply != held_reply || refs != 1) return false;
    /* The typed kernel operation independently refuses a live SEND_ONCE right;
     * no polymorphic deallocate/destructor or retry may replace this operation.
     * Exclusive retained-name ownership excludes release/replacement by another
     * in-process actor; this is not arbitrary memory-corruption protection. */
    r = mach_port_mod_refs(mach_task_self(), held_reply, MACH_PORT_RIGHT_DEAD_NAME, -1);
    if (r != KERN_SUCCESS) { o->uncertain = true; return false; }
    o->reply_released = true; /* Record actual effect before the next boundary. */
    o->request_reply = MACH_PORT_NULL;
    if (clock_ns() >= o->cleanup_end || o->integrity_refused) return false;
    o->reply_retired_timely = true;
    return true;
}

bool hmp_admission_owner_retire_dead_reply(hmp_admission_owner *o) {
    if (!enter(o)) return false;
    bool result = retire_dead_reply(o);
    return leave(o, result);
}
