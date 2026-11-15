/* Fresh fixed parent/child only. One request to an explicitly assigned owned
 * endpoint; child owns the reply destination. No reply/challenge/global name. */
#include <bsm/libbsm.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <mach/mach.h>
#include <mach/thread_status.h>
#include <mach-o/dyld.h>
#include <poll.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#include "hmp_admission_owner.c"

#define CONTROL_FD 198
struct copied_policy {
    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_port_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];
    mach_msg_type_number_t count;
    bool known;
};
static bool query_policy(struct copied_policy *p) {
    memset(p, 0, sizeof(*p)); p->count = EXC_TYPES_COUNT;
    kern_return_t r = task_get_exception_ports(mach_task_self(), EXC_MASK_BREAKPOINT,
        p->masks, &p->count, p->ports, p->behaviors, p->flavors);
    p->known = r == KERN_SUCCESS && p->count <= EXC_TYPES_COUNT;
    return p->known;
}
static bool release_policy(struct copied_policy *p) {
    if (!p->known) return false;
    bool known = true;
    for (mach_msg_type_number_t i = 0; i < p->count; ++i)
        if (MACH_PORT_VALID(p->ports[i]) &&
            mach_port_deallocate(mach_task_self(), p->ports[i]) != KERN_SUCCESS) known = false;
    return known;
}
static bool close_once(int *fd) {
    if (*fd < 0) return true;
    int original = *fd; *fd = -1; /* Retire numeric close permission before syscall. */
    return close(original) == 0;
}
static bool eof_before(uint64_t end) {
    while (clock_ns() < end) {
        struct pollfd p = {.fd = CONTROL_FD, .events = POLLIN | POLLHUP};
        int r = poll(&p, 1, 10);
        if (r < 0 && errno == EINTR) continue;
        if (r < 0 || (r > 0 && (p.revents & (POLLERR | POLLNVAL)))) return false;
        if (r > 0) {
            unsigned char byte;
            ssize_t count = read(CONTROL_FD, &byte, 1);
            if (count == 0) return clock_ns() < end;
            if (count < 0 && (errno == EINTR || errno == EAGAIN)) continue;
            return false; /* No control bytes are part of this fixture. */
        }
    }
    return false;
}
static int sender(uint64_t end, uint64_t cleanup_end) {
    alarm(10); /* Secondary fresh-child bound, never parent/gateway policy. */
    struct stat st;
    int flags = fcntl(CONTROL_FD, F_GETFL);
    bool pipe_valid = fstat(CONTROL_FD, &st) == 0 && S_ISFIFO(st.st_mode) &&
        st.st_uid == geteuid() && flags >= 0 && (flags & O_ACCMODE) == O_RDONLY &&
        (flags & O_NONBLOCK) != 0;
    struct copied_policy assigned, clear;
    bool queried = query_policy(&assigned);
    bool shape = queried && assigned.count == 1 &&
        assigned.masks[0] == EXC_MASK_BREAKPOINT && MACH_PORT_VALID(assigned.ports[0]) &&
        assigned.behaviors[0] == EXCEPTION_DEFAULT && assigned.flavors[0] == THREAD_STATE_NONE;
    bool cleared = task_set_exception_ports(mach_task_self(), EXC_MASK_BREAKPOINT,
        MACH_PORT_NULL, EXCEPTION_DEFAULT, THREAD_STATE_NONE) == KERN_SUCCESS;
    bool readback = query_policy(&clear);
    for (mach_msg_type_number_t i = 0; readback && i < clear.count; ++i)
        if (clear.ports[i] != MACH_PORT_NULL) cleared = false;
    cleared = cleared && readback;
    mach_port_t reply = MACH_PORT_NULL;
    bool reply_owned = false, sent = false, eof = false, reply_closed = false;
    if (!pipe_valid || !shape || !cleared || clock_ns() >= end) goto cleanup;
    if (mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &reply) != KERN_SUCCESS)
        goto cleanup;
    reply_owned = true;
    struct hmp_initial_request message = {0};
    message.header.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_COPY_SEND, MACH_MSG_TYPE_MAKE_SEND_ONCE);
    message.header.msgh_size = sizeof(message);
    message.header.msgh_remote_port = assigned.ports[0];
    message.header.msgh_local_port = reply;
    message.header.msgh_id = HMP_REQUEST_ID;
    message.schema = message.phase = 1;
    uint64_t before_send = clock_ns();
    if (before_send >= end) goto cleanup;
    uint64_t remaining = end - before_send;
    uint64_t milliseconds = remaining / 1000000 + (remaining % 1000000 != 0);
    mach_msg_timeout_t timeout = (mach_msg_timeout_t)(milliseconds > 1000 ? 1000 : milliseconds);
    if (timeout == 0) goto cleanup;
    sent = mach_msg(&message.header, MACH_SEND_MSG | MACH_SEND_TIMEOUT, sizeof(message), 0,
        MACH_PORT_NULL, timeout, MACH_PORT_NULL) == MACH_MSG_SUCCESS && clock_ns() < end;
    if (sent) eof = eof_before(end);
cleanup:
    if (reply_owned && clock_ns() < cleanup_end)
        reply_closed = mach_port_mod_refs(mach_task_self(), reply,
            MACH_PORT_RIGHT_RECEIVE, -1) == KERN_SUCCESS;
    bool assigned_refs = release_policy(&assigned);
    bool clear_refs = release_policy(&clear);
    int control = CONTROL_FD;
    bool pipe_closed = close_once(&control);
    return pipe_valid && shape && cleared && sent && eof && reply_closed && assigned_refs &&
        clear_refs && pipe_closed && clock_ns() < cleanup_end ? 0 : 1;
}
static bool wait_until(pid_t child, uint64_t end, int *status, bool *reaped) {
    while (clock_ns() < end) {
        pid_t r = waitpid(child, status, WNOHANG);
        if (r == child) { *reaped = true; return true; }
        if (r < 0 && errno != EINTR) return false; /* No PID-signal permission. */
        struct timespec pause = {.tv_nsec = 1000000}; nanosleep(&pause, NULL);
    }
    return false;
}
static const char *yes(bool b) { return b ? "true" : "false"; }
int main(int argc, char **argv) {
    struct sigaction policy = {.sa_handler = SIG_DFL};
    if (geteuid() == 0 || geteuid() != getuid() || sigemptyset(&policy.sa_mask) != 0 ||
        sigaction(SIGCHLD, &policy, NULL) != 0 || sigaction(SIGALRM, &policy, NULL) != 0) return 64;
    if (argc == 5 && strcmp(argv[1], "--sender") == 0) {
        char *a, *b, *c; errno = 0;
        unsigned long long end = strtoull(argv[2], &a, 10), cleanup = strtoull(argv[3], &b, 10);
        long parent = strtol(argv[4], &c, 10); uint64_t now = clock_ns();
        if (errno || a == argv[2] || b == argv[3] || c == argv[4] || *a || *b || *c ||
            parent <= 1 || parent > INT_MAX || getppid() != parent || end <= now ||
            cleanup < end || cleanup - now > 10000000000ULL) return 65;
        return sender(end, cleanup);
    }
    if (argc != 1) return 64;
    uint64_t start = clock_ns();
    if (start == UINT64_MAX || start > UINT64_MAX - 8000000000ULL) return 65;
    const uint64_t end = start + 5000000000ULL, cleanup_end = start + 8000000000ULL;
    hmp_admission_owner *owner = hmp_admission_owner_allocate();
    int pipes[2] = {-1, -1}, status = 0;
    pid_t child = -1;
    bool spawned = false, reaped = false, settlement = false, pipe_closes = true;
    bool attr_ready = false, actions_ready = false, attr_destroyed = false, actions_destroyed = false;
    bool observed = false, matched = false, retired = false, closed = false, disposed = false;
    bool absent = false, initialized = false;
    posix_spawnattr_t attr; posix_spawn_file_actions_t actions;
    if (owner == NULL) goto cleanup;
    initialized = hmp_admission_owner_initialize(owner, end, cleanup_end);
    if (!initialized || fcntl(CONTROL_FD, F_GETFD) >= 0 || errno != EBADF) goto cleanup;
    if (pipe(pipes) != 0) goto cleanup; /* Both actual descriptors retained before effects. */
    if (pipes[0] == CONTROL_FD || pipes[1] == CONTROL_FD) goto cleanup;
    if (fcntl(pipes[0], F_SETFD, FD_CLOEXEC) != 0 || fcntl(pipes[1], F_SETFD, FD_CLOEXEC) != 0 ||
        fcntl(pipes[0], F_SETFL, O_NONBLOCK) != 0) goto cleanup;
    if (posix_spawnattr_init(&attr) != 0) goto cleanup;
    attr_ready = true;
    if (posix_spawnattr_setflags(&attr, POSIX_SPAWN_CLOEXEC_DEFAULT) != 0 ||
        posix_spawnattr_setexceptionports_np(&attr, EXC_MASK_BREAKPOINT, owner->endpoint,
            EXCEPTION_DEFAULT, THREAD_STATE_NONE) != 0) goto cleanup;
    if (posix_spawn_file_actions_init(&actions) != 0) goto cleanup;
    actions_ready = true;
    if (posix_spawn_file_actions_adddup2(&actions, pipes[0], CONTROL_FD) != 0 ||
        posix_spawn_file_actions_addclose(&actions, pipes[0]) != 0 ||
        posix_spawn_file_actions_addclose(&actions, pipes[1]) != 0) goto cleanup;
    char executable[PATH_MAX], resolved[PATH_MAX], end_text[32], cleanup_text[32], parent_text[32];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) != 0 || realpath(executable, resolved) == NULL)
        goto cleanup;
    snprintf(end_text, sizeof(end_text), "%llu", (unsigned long long)end);
    snprintf(cleanup_text, sizeof(cleanup_text), "%llu", (unsigned long long)cleanup_end);
    snprintf(parent_text, sizeof(parent_text), "%ld", (long)getpid());
    char *args[] = {resolved, "--sender", end_text, cleanup_text, parent_text, NULL};
    char *env[] = {"PATH=/usr/bin:/bin", "LANG=C", "LC_ALL=C", NULL};
    if (clock_ns() >= end || posix_spawn(&child, resolved, &actions, &attr, args, env) != 0)
        goto cleanup;
    if (child <= 1) {
        /* Successful native creation with an unusable identity is not permission
         * to exit/orphan, reap broadly or signal a guessed PID. Retain this
         * helper and all partial owners; the controller observes the same actor. */
        fputs("owned_spawn_identity_unknown; retaining settlement\n", stderr);
        for (;;) {
            struct timespec pause = {.tv_sec = 1}; nanosleep(&pause, NULL);
        }
    }
    spawned = true;
    pipe_closes = close_once(&pipes[0]);
    observed = hmp_admission_owner_observe_request(owner);
    matched = observed && owner->observed_pid == child && owner->observed_uid == geteuid();
    if (!matched) goto cleanup;
    pipe_closes = close_once(&pipes[1]) && pipe_closes; /* Exact child match precedes positive EOF. */
cleanup:
    /* Cleanup EOF is cancellation, not successful admission or request matching. */
    pipe_closes = close_once(&pipes[0]) && pipe_closes;
    pipe_closes = close_once(&pipes[1]) && pipe_closes;
    if (actions_ready) actions_destroyed = posix_spawn_file_actions_destroy(&actions) == 0;
    if (attr_ready) attr_destroyed = posix_spawnattr_destroy(&attr) == 0;
    if (spawned) {
        (void)wait_until(child, cleanup_end, &status, &reaped);
        while (!reaped) {
            settlement = true; /* Retain exact child; no signal, restart or parent exit. */
            pid_t result = waitpid(child, &status, WNOHANG);
            if (result == child) reaped = true;
            else {
                struct timespec pause = {.tv_nsec = 1000000};
                nanosleep(&pause, NULL); /* Clock failure cannot overflow a new deadline. */
            }
        }
    }
    bool child_report = spawned && reaped && WIFEXITED(status) && WEXITSTATUS(status) == 0;
    if (matched && child_report) retired = hmp_admission_owner_retire_dead_reply(owner);
    mach_port_t old_port = owner == NULL ? MACH_PORT_NULL : owner->endpoint;
    if (owner != NULL) closed = hmp_admission_owner_close(owner);
    mach_port_type_t type = 0;
    absent = closed && mach_port_type(mach_task_self(), old_port, &type) == KERN_INVALID_NAME;
    if (closed) disposed = hmp_admission_owner_dispose(&owner);
    bool timely = clock_ns() < cleanup_end;
    bool passed = observed && matched && child_report && retired && closed && absent && disposed &&
        pipe_closes && attr_destroyed && actions_destroyed && timely && !settlement;
    printf("{\"schema\":1,\"request_observed\":%s,\"kernel_child_match\":%s,"
        "\"child_wait_known\":%s,\"child_exit0_reported_cleanup\":%s,\"dead_reply_retired\":%s,"
        "\"endpoint_close_known\":%s,\"endpoint_name_absent\":%s,\"owner_disposed\":%s,"
        "\"pipe_closes_known\":%s,\"spawn_attributes_destroyed\":%s,\"spawn_actions_destroyed\":%s,"
        "\"cleanup_within_deadline\":%s,\"settlement_only_used\":%s,\"production_qualified\":false}\n",
        yes(observed), yes(matched), yes(reaped), yes(child_report), yes(retired), yes(closed),
        yes(absent), yes(disposed), yes(pipe_closes), yes(attr_destroyed), yes(actions_destroyed),
        yes(timely), yes(settlement));
    return passed ? 0 : 1;
}
