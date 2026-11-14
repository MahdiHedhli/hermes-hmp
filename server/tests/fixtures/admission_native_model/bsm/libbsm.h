/* Model-only token accessors; these are not a kernel ABI/identity claim. */
#ifndef HMP_TEST_BSM_H
#define HMP_TEST_BSM_H
#include <mach/mach.h>
#include <sys/types.h>
pid_t audit_token_to_pid(audit_token_t);
uid_t audit_token_to_euid(audit_token_t);
int audit_token_to_pidversion(audit_token_t);
#endif
