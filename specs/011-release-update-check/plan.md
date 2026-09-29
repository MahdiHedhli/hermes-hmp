# Plan

1. Add an import-safe, read-only operator CLI subcommand.
2. Resolve the latest published tag to a full commit through fixed GitHub API
   endpoints. Compare installed and candidate commit ancestry.
3. Read the candidate's four published compatibility manifests by commit SHA;
   validate bounded paths and match the local Hermes build without importing
   candidate code.
4. Test synthetic release/network/metadata paths and document manual update,
   isolated validation, and rollback.
5. Publish a reviewed release separately; no tag or live install is created by
   this implementation branch.
