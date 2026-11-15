/* Disposable, single-threaded Darwin message-origin experiment.
 * Only new fixture rights and the fresh child's selected exception assignment change.
 * No global bootstrap name, gateway, provider, native home or application IPC.
 * Kernel sender data is not executable-origin or production issuer authority.
 */
#include <bsm/libbsm.h>
#include <errno.h>
#include <limits.h>
#include <mach/mach.h>
#include <mach/message.h>
#include <mach/thread_status.h>
#include <mach-o/dyld.h>
#include <signal.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

_Static_assert(sizeof(mach_msg_header_t) == 24, "unsupported Mach header ABI");
_Static_assert(sizeof(mach_msg_audit_trailer_t) == 52, "unsupported audit trailer ABI");

enum { BODY_LIMIT = 512, FIRST_ID = 0x484d5001 };
static const uint32_t MARKER = 0x534e4452;

struct wire_message {
    mach_msg_header_t header;
    uint32_t schema;
    uint32_t claimed_pid;
    uint32_t marker;
};
struct spoofed_message {
    struct wire_message normal;
    mach_msg_audit_trailer_t fake_body_trailer;
};
_Static_assert(sizeof(struct wire_message) == 36, "unexpected body padding");

static uint64_t now_ns(void) {
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0 || value.tv_sec < 0 ||
        (uint64_t)value.tv_sec > (UINT64_MAX - 999999999) / 1000000000) {
        return UINT64_MAX;
    }
    return (uint64_t)value.tv_sec * 1000000000 + (uint64_t)value.tv_nsec;
}

static mach_msg_timeout_t remaining_ms(uint64_t end) {
    uint64_t now = now_ns();
    if (now >= end) return 0;
    uint64_t value = (end - now + 999999) / 1000000;
    /* Every call is finite and also shares the original absolute deadline. */
    return (mach_msg_timeout_t)(value > 1000 ? 1000 : value);
}

struct policy {
    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];
    mach_msg_type_number_t count;
    bool known;
};

static bool get_policy(struct policy *value, exception_mask_t mask) {
    memset(value, 0, sizeof(*value));
    value->count = EXC_TYPES_COUNT;
    kern_return_t result = task_get_exception_ports(mach_task_self(), mask, value->masks,
        &value->count, value->ports, value->behaviors, value->flavors);
    value->known = result == KERN_SUCCESS && value->count <= EXC_TYPES_COUNT;
    return value->known;
}

static bool release_policy(struct policy *value) {
    if (!value->known) return false;
    bool released = true;
    for (mach_msg_type_number_t i = 0; i < value->count; ++i) {
        /* Each getter returns a copied send reference, never a receive right. */
        if (MACH_PORT_VALID(value->ports[i]) &&
            mach_port_deallocate(mach_task_self(), value->ports[i]) != KERN_SUCCESS) released = false;
    }
    return released;
}

static bool same_policy(const struct policy *before, const struct policy *after) {
    if (!before->known || !after->known || before->count != after->count) return false;
    for (mach_msg_type_number_t i = 0; i < before->count; ++i) {
        if (before->masks[i] != after->masks[i] || before->ports[i] != after->ports[i] ||
            before->behaviors[i] != after->behaviors[i] ||
            before->flavors[i] != after->flavors[i]) return false;
    }
    return true;
}

static bool wait_exact(pid_t child, uint64_t end, int *status, bool *reaped, bool *can_signal) {
    while (now_ns() < end) {
        pid_t result = waitpid(child, status, WNOHANG);
        if (result == child) {
            *reaped = true;
            *can_signal = false;
            return true;
        }
        if ((result < 0 && errno != EINTR) || result > 0) {
            *can_signal = false;  /* ECHILD/uncertainty never authorizes a PID signal */
            return false;
        }
        struct timespec pause = { .tv_sec = 0, .tv_nsec = 1000000 };
        nanosleep(&pause, NULL);
    }
    return false;
}

static int child_send(uint64_t end) {
    alarm(4);  /* additional independent fixture bound; not an HMP allowance */
    struct policy assigned;
    bool queried = get_policy(&assigned, EXC_MASK_BREAKPOINT);
    bool shape = queried && assigned.count == 1 &&
        assigned.masks[0] == EXC_MASK_BREAKPOINT && MACH_PORT_VALID(assigned.ports[0]) &&
        assigned.behaviors[0] == EXCEPTION_DEFAULT && assigned.flavors[0] == THREAD_STATE_NONE;
    /* The public spawn attribute installed our parent's owned right into this
     * new child. This is not a runtime-managed registered slot. Clear it before
     * any fixture sends; retain only the getter's copied send reference. */
    bool cleared = task_set_exception_ports(mach_task_self(), EXC_MASK_BREAKPOINT,
        MACH_PORT_NULL, EXCEPTION_DEFAULT, THREAD_STATE_NONE) == KERN_SUCCESS;
    struct policy clear_readback;
    bool readback_known = get_policy(&clear_readback, EXC_MASK_BREAKPOINT);
    if (!readback_known) cleared = false;
    for (mach_msg_type_number_t i = 0; readback_known && i < clear_readback.count; ++i) {
        if (clear_readback.ports[i] != MACH_PORT_NULL) cleared = false;
    }
    bool sent = false;
    if (!shape || !cleared || now_ns() >= end) goto cleanup;
    for (unsigned int i = 0; i < 2; ++i) {
        struct spoofed_message message;
        memset(&message, 0, sizeof(message));
        message.normal.header.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, 0);
        message.normal.header.msgh_size = (mach_msg_size_t)(i == 0 ?
            sizeof(struct wire_message) : sizeof(struct spoofed_message));
        message.normal.header.msgh_remote_port = assigned.ports[0];
        message.normal.header.msgh_id = FIRST_ID + (mach_msg_id_t)i;
        message.normal.schema = 1;
        message.normal.claimed_pid = 1;  /* intentionally false, never authority */
        message.normal.marker = MARKER;
        message.fake_body_trailer.msgh_trailer_type = MACH_MSG_TRAILER_FORMAT_0;
        message.fake_body_trailer.msgh_trailer_size = sizeof(mach_msg_audit_trailer_t);
        mach_msg_timeout_t timeout = remaining_ms(end);
        if (timeout == 0 || mach_msg(&message.normal.header, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
                message.normal.header.msgh_size, 0, MACH_PORT_NULL, timeout,
                MACH_PORT_NULL) != MACH_MSG_SUCCESS || now_ns() >= end) goto cleanup;
    }
    sent = true;
cleanup:
    ;  /* C11 label must precede a statement. */
    bool refs = release_policy(&assigned);
    bool readback_refs = release_policy(&clear_readback);
    refs = refs && readback_refs;
    unsigned int failures = (!sent ? 1u : 0u) | (!cleared ? 2u : 0u) |
                            (!refs ? 4u : 0u) | (!shape ? 8u : 0u);
    /* A closed diagnostic exit mask, not an authorization/closure capability. */
    return failures == 0 ? 0 : (int)(0x60u | failures);
}

static bool receive_one(mach_port_t port, pid_t original_child, uid_t original_uid,
                        unsigned int index, uint64_t end, int *version,
                        bool *body_accepted, kern_return_t *native_error,
                        bool *unexpected_received, bool *destroy_attempted,
                        bool *copyout_unknown) {
    union {
        mach_msg_header_t alignment;
        unsigned char bytes[BODY_LIMIT + MAX_TRAILER_SIZE];
    } buffer;
    memset(&buffer, 0, sizeof(buffer));
    mach_msg_header_t *header = (mach_msg_header_t *)buffer.bytes;
    mach_msg_timeout_t timeout = remaining_ms(end);
    if (timeout == 0) return false;
    *native_error = mach_msg(header, MACH_RCV_MSG | MACH_RCV_TIMEOUT |
        MACH_RCV_TRAILER_TYPE(MACH_MSG_TRAILER_FORMAT_0) |
        MACH_RCV_TRAILER_ELEMENTS(MACH_RCV_TRAILER_AUDIT), 0,
        (mach_msg_size_t)sizeof(buffer), port, timeout, MACH_PORT_NULL);
    if (*native_error != MACH_MSG_SUCCESS) {
        if (*native_error != MACH_RCV_TIMED_OUT) *copyout_unknown = true;
        return false;
    }
    if (header->msgh_size < sizeof(mach_msg_header_t) || header->msgh_size > sizeof(buffer)) {
        *copyout_unknown = true;
        return false;
    }
    if ((header->msgh_bits & MACH_MSGH_BITS_COMPLEX) != 0 ||
        header->msgh_remote_port != MACH_PORT_NULL || header->msgh_voucher_port != MACH_PORT_NULL) {
        *unexpected_received = true;
        /* Only this actual kernel-delivered message. The library destroys its
         * remote/voucher/body rights; it does not destroy the borrowed local
         * receive right. A void destructor is an attempt, not cleanup proof. */
        mach_msg_destroy(header);
        *destroy_attempted = true;
        return false;
    }
    if (now_ns() >= end) return false;  /* rights disposal precedes the time refusal */
    if (header->msgh_size < sizeof(struct wire_message) || header->msgh_size > BODY_LIMIT ||
        header->msgh_local_port != port ||
        header->msgh_id != FIRST_ID + (mach_msg_id_t)index) return false;
    size_t offset = ((size_t)header->msgh_size + 3u) & ~(size_t)3u;
    if (offset > sizeof(buffer.bytes) - sizeof(mach_msg_audit_trailer_t)) return false;
    mach_msg_audit_trailer_t trailer;
    memcpy(&trailer, buffer.bytes + offset, sizeof(trailer));
    if (trailer.msgh_trailer_type != MACH_MSG_TRAILER_FORMAT_0 ||
        trailer.msgh_trailer_size != sizeof(trailer)) return false;
    /* The token is opaque. The SDK's library accessors, not token indices or
     * caller-controlled body fields, supply sender-at-message identity. */
    int current_version = audit_token_to_pidversion(trailer.msgh_audit);
    if (audit_token_to_pid(trailer.msgh_audit) != original_child ||
        audit_token_to_euid(trailer.msgh_audit) != original_uid || current_version < 0 ||
        (index != 0 && *version != current_version)) return false;
    *version = current_version;
    struct wire_message body;
    memcpy(&body, buffer.bytes, sizeof(body));
    if (body.claimed_pid != 1 || body.claimed_pid == (uint32_t)original_child ||
        body.schema != 1 || body.marker != MARKER) return false;
    *body_accepted = header->msgh_size == sizeof(struct wire_message);
    /* The extended fake trailer remains body data, not the kernel trailer. */
    bool expected_shape = index == 0 ? *body_accepted :
        (!*body_accepted && header->msgh_size == sizeof(struct spoofed_message));
    return expected_shape && now_ns() < end;
}

static const char *yes(bool value) { return value ? "true" : "false"; }

static bool own_signal_policy(void) {
    struct sigaction action, current;
    memset(&action, 0, sizeof(action));
    action.sa_handler = SIG_DFL;
    return sigemptyset(&action.sa_mask) == 0 && sigaction(SIGALRM, &action, NULL) == 0 &&
        sigaction(SIGTERM, &action, NULL) == 0 && sigaction(SIGCHLD, &action, NULL) == 0 &&
        sigaction(SIGCHLD, NULL, &current) == 0 && current.sa_handler == SIG_DFL &&
        (current.sa_flags & SA_NOCLDWAIT) == 0;
}

int main(int argc, char **argv) {
    if (geteuid() == 0 || geteuid() != getuid() || !own_signal_policy()) return 64;
    if (argc == 4 && strcmp(argv[1], "--sender") == 0) {
        char *end_pointer = NULL, *parent_pointer = NULL;
        errno = 0;
        unsigned long long parsed_end = strtoull(argv[2], &end_pointer, 10);
        if (errno != 0 || end_pointer == argv[2] || *end_pointer != '\0') return 65;
        errno = 0;
        long parsed_parent = strtol(argv[3], &parent_pointer, 10);
        uint64_t now = now_ns();
        if (errno != 0 || parent_pointer == argv[3] || *parent_pointer != '\0' ||
            parsed_parent <= 1 || parsed_parent > INT_MAX || getppid() != (pid_t)parsed_parent ||
            parsed_end <= now || parsed_end - now > 5000000000) return 65;
        return child_send((uint64_t)parsed_end);
    }
    if (argc != 1) return 64;
    const uint64_t start = now_ns();
    if (start == UINT64_MAX || start > UINT64_MAX - 8000000000) return 65;
    const uint64_t end = start + 5000000000, cleanup_end = start + 7000000000;
    const uid_t original_uid = geteuid();
    mach_port_t receive = MACH_PORT_NULL;
    struct policy before = {0}, after = {0};
    bool before_refs = false, after_refs = false, parent_policy_unchanged = false;
    bool own_send_created = false, own_send_released = false, receive_released = false;
    bool attributes_initialized = false, attributes_destroyed = false, assignment_configured = false;
    bool spawn_known = false, reaped = false, can_signal = false, child_exit0 = false;
    bool observation_timely = false, settlement_only = false;
    bool child_report_valid = false, child_refs = false, child_clear = false, child_shape = false;
    bool unexpected_received = false, unexpected_destroy_attempted = false;
    bool copyout_unknown = false;
    bool bodies[2] = {false, false}, observed[2] = {false, false};
    pid_t child = -1;
    int status = 0, version = -1, spawn_error = 0;
    kern_return_t error = KERN_SUCCESS;
    posix_spawnattr_t attributes;
    const char *stage = "parent_policy_before";
    if (!get_policy(&before, EXC_MASK_ALL)) goto cleanup;
    stage = "allocate_own_port";
    error = mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &receive);
    if (error != KERN_SUCCESS) goto cleanup;
    error = mach_port_insert_right(mach_task_self(), receive, receive, MACH_MSG_TYPE_MAKE_SEND);
    if (error != KERN_SUCCESS) goto cleanup;
    own_send_created = true;
    mach_port_limits_t limits;
    mach_msg_type_number_t limits_count = MACH_PORT_LIMITS_INFO_COUNT;
    error = mach_port_get_attributes(mach_task_self(), receive, MACH_PORT_LIMITS_INFO,
                                     (mach_port_info_t)&limits, &limits_count);
    if (error != KERN_SUCCESS || limits_count != MACH_PORT_LIMITS_INFO_COUNT ||
        limits.mpl_qlimit < 2) goto cleanup;
    stage = "configure_new_child_only";
    spawn_error = posix_spawnattr_init(&attributes);
    if (spawn_error != 0) goto cleanup;
    attributes_initialized = true;
    spawn_error = posix_spawnattr_setflags(&attributes, POSIX_SPAWN_CLOEXEC_DEFAULT);
    if (spawn_error != 0) goto cleanup;
    spawn_error = posix_spawnattr_setexceptionports_np(&attributes, EXC_MASK_BREAKPOINT,
        receive, EXCEPTION_DEFAULT, THREAD_STATE_NONE);
    if (spawn_error != 0) goto cleanup;
    assignment_configured = true;
    char executable[PATH_MAX], resolved[PATH_MAX], end_text[32], parent_text[32];
    uint32_t executable_size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &executable_size) != 0 ||
        realpath(executable, resolved) == NULL || now_ns() >= end) goto cleanup;
    (void)snprintf(end_text, sizeof(end_text), "%llu", (unsigned long long)end);
    (void)snprintf(parent_text, sizeof(parent_text), "%ld", (long)getpid());
    char *child_argv[] = {resolved, "--sender", end_text, parent_text, NULL};
    char *child_env[] = {"LANG=C", "LC_ALL=C", "PATH=/usr/bin:/bin", NULL};
    stage = "spawn_fixed_own_child";
    spawn_error = posix_spawn(&child, resolved, NULL, &attributes, child_argv, child_env);
    if (spawn_error != 0 || child <= 1) goto cleanup;
    spawn_known = can_signal = true;
    attributes_destroyed = posix_spawnattr_destroy(&attributes) == 0;
    if (!attributes_destroyed) goto cleanup;
    stage = "exact_child_wait";
    if (!wait_exact(child, end, &status, &reaped, &can_signal)) goto cleanup;
    child_exit0 = WIFEXITED(status) && WEXITSTATUS(status) == 0;
    if (!child_exit0) goto cleanup;
    stage = "receive_queued_audit";
    for (unsigned int i = 0; i < 2; ++i) {
        observed[i] = receive_one(receive, child, original_uid, i, end, &version, &bodies[i],
            &error, &unexpected_received, &unexpected_destroy_attempted, &copyout_unknown);
        if (!observed[i]) break;
    }
    observation_timely = observed[0] && observed[1] && now_ns() < end;
    if (observation_timely) stage = "observed";
cleanup:
    if (attributes_initialized && !attributes_destroyed) {
        /* A failed destroy is not retried; preserve unknown cleanup. */
        if (!spawn_known) attributes_destroyed = posix_spawnattr_destroy(&attributes) == 0;
    }
    if (spawn_known && !reaped) {
        if (can_signal && now_ns() < cleanup_end) {
            (void)kill(child, SIGTERM);  /* only this exact owned unreaped child */
            (void)wait_exact(child, cleanup_end, &status, &reaped, &can_signal);
        }
        if (!reaped) {
            settlement_only = true;
            stage = "child_settlement_only";
            fputs("owned_child_settlement_pending\n", stderr);
            fflush(stderr);
            while (!reaped) {
                pid_t result = waitpid(child, &status, WNOHANG);
                if (result == child) {
                    reaped = true;
                    can_signal = false;
                } else {
                    if ((result < 0 && errno != EINTR) || result > 0) can_signal = false;
                    struct timespec pause = {.tv_sec = 0, .tv_nsec = 100000000};
                    nanosleep(&pause, NULL);
                }
            }
        }
    }
    if (reaped && WIFEXITED(status)) {
        unsigned int code = (unsigned int)WEXITSTATUS(status);
        child_exit0 = code == 0;
        child_report_valid = code == 0 || (code > 0x60u && code <= 0x6fu);
        child_clear = child_report_valid && (code == 0 || (code & 2u) == 0);
        child_refs = child_report_valid && (code == 0 || (code & 4u) == 0);
        child_shape = child_report_valid && (code == 0 || (code & 8u) == 0);
    }
    bool after_known = get_policy(&after, EXC_MASK_ALL);
    parent_policy_unchanged = after_known && same_policy(&before, &after);
    before_refs = release_policy(&before);
    after_refs = release_policy(&after);
    if (MACH_PORT_VALID(receive)) {
        receive_released = mach_port_mod_refs(mach_task_self(), receive,
                                              MACH_PORT_RIGHT_RECEIVE, -1) == KERN_SUCCESS;
        own_send_released = !own_send_created ||
            mach_port_deallocate(mach_task_self(), receive) == KERN_SUCCESS;
    }
    bool resources_known = parent_policy_unchanged && before_refs && after_refs &&
        receive_released && own_send_released && attributes_destroyed && reaped && !can_signal &&
        !unexpected_received && !copyout_unknown;
    bool late_cleanup = now_ns() >= cleanup_end;
    bool cleanup_timely = !late_cleanup && !settlement_only;
    bool clean = resources_known && cleanup_timely;
    bool success = observation_timely && bodies[0] && !bodies[1] && child_exit0 && clean &&
        assignment_configured && spawn_known && child_clear && child_refs && child_shape;
    printf("{\"schema\":2,\"stage\":\"%s\",\"observed\":%s,"
        "\"messages_received\":%u,\"receipt_after_sender_exit\":%s,"
        "\"body_pid_ignored\":%s,\"extended_body_refused\":%s,"
        "\"kernel_sender_matches_owned_child\":%s,\"sender_version_consistent\":%s,"
        "\"destination_assigned_by_spawn\":%s,\"parent_exception_policy_unchanged\":%s,"
        "\"parent_before_refs_released\":%s,\"parent_after_refs_released\":%s,"
        "\"spawn_attributes_destroyed\":%s,\"own_receive_right_released\":%s,"
        "\"own_send_right_released\":%s,\"exact_child_wait_known\":%s,"
        "\"child_exit0_after_local_cleanup\":%s,\"own_child_policy_known\":true,"
        "\"signal_permission_retired\":%s,\"child_cleanup_report_valid\":%s,"
        "\"child_reported_assignment_cleared\":%s,\"child_reported_refs_released\":%s,"
        "\"child_reported_destination_shape\":%s,\"unexpected_message_received\":%s,"
        "\"unexpected_message_destroy_attempted\":%s,\"observation_within_deadline\":%s,"
        "\"receive_copyout_unknown\":%s,"
        "\"cleanup_resources_known\":%s,\"cleanup_within_deadline\":%s,"
        "\"late_cleanup\":%s,\"settlement_only_used\":%s,\"cleanup_known\":%s,"
        "\"mach_error\":%d,\"spawn_error\":%d,\"production_qualified\":false}\n",
        stage, yes(success), (unsigned int)observed[0] + (unsigned int)observed[1],
        yes(observation_timely && reaped && child_exit0), yes(observed[0]),
        yes(observed[1] && !bodies[1]), yes(observed[0] && observed[1]),
        yes(observed[0] && observed[1]), yes(assignment_configured && spawn_known),
        yes(parent_policy_unchanged), yes(before_refs), yes(after_refs), yes(attributes_destroyed),
        yes(receive_released), yes(own_send_released), yes(reaped), yes(child_exit0),
        yes(!can_signal), yes(child_report_valid), yes(child_clear), yes(child_refs), yes(child_shape),
        yes(unexpected_received), yes(unexpected_destroy_attempted), yes(observation_timely),
        yes(copyout_unknown), yes(resources_known), yes(cleanup_timely), yes(late_cleanup),
        yes(settlement_only),
        yes(clean), (int)error, spawn_error);
    return success ? 0 : 1;
}
