# Infrastructure Drift Monitor

A small Python command that turns a Terraform JSON plan into a resource-level drift report. It reads a file; it does not connect to your cloud account, change state, or run `terraform apply`.

**Status:** initial implementation. No local tests or live Terraform validation have been performed. The example below is synthetic, not evidence from a deployed environment.

## Why this exists

A normal plan can mix two different questions: what changed outside Terraform, and what Terraform proposes to do next. This command keeps them separate. By default it reads `resource_drift`. With `--planned`, it reads `resource_changes` instead and labels the output accordingly.

## Requirements

- Python 3.9+; standard library only.
- Terraform and provider credentials are needed to produce a real plan, not to read the example.
- Supported input: Terraform JSON plan format major version 1.

## Try the report

```bash
python3 drift.py examples/drift.json
python3 drift.py examples/drift.json --format json
```

Expected text output (illustrative; not a captured execution):

```text
recorded_drift: 1 resource(s)
"aws_s3_bucket.example": update
```

An exit code of **2** means findings were reported; it is not a parser error.

## Capture real drift

Run these commands in an initialized Terraform working directory with the correct backend, workspace, variables, and read permissions:

```bash
umask 077
terraform plan -refresh-only -out=drift.tfplan
terraform show -json drift.tfplan > plan.json
python3 /path/to/infrastructure-drift-monitor/drift.py plan.json --format json > drift-report.json
```

`plan -refresh-only` reads provider APIs and takes the normal state lock where supported; it does not apply the resulting state changes. Supply any normal `-var-file` options your configuration requires. Do not apply a refresh-only plan merely to silence a finding: accepting a state update is a separate decision.

Plan files and JSON exports can contain sensitive plaintext even when Terraform marks attributes sensitive. Keep the source files private. This report omits before/after values, but resource addresses themselves may still reveal internal names.

## Command reference

| Argument | Meaning |
| --- | --- |
| `plan` | Path to a saved plan exported with `terraform show -json` |
| `--format text` | Human-readable summary; default |
| `--format json` | Structured report for another script |
| `--planned` | Inspect proposed changes, not recorded drift |

Exit codes: `0` = no findings in the selected section; `2` = findings; `1` = unreadable or unsupported input.

For shell automation, handle the finding code explicitly:

```bash
result=0
python3 drift.py plan.json --format json > drift-report.json || result=$?
case "$result" in
  0) echo "No recorded drift" ;;
  2) echo "Review drift-report.json before deciding on remediation" ;;
  *) echo "Report generation failed" >&2; exit "$result" ;;
esac
```

## Review and remediation

1. Confirm the plan is recent and came from the intended workspace.
2. Inspect the affected resource through your normal secure workflow.
3. Decide whether the external change was intentional.
4. For an intentional change, update configuration in a pull request and inspect a fresh normal plan.
5. For an unintended change, inspect a normal plan that restores the desired configuration. Apply only through the usual approval process.

The command never proposes or executes an automatic correction.

## Design limits

- No scheduler, cloud SDK, UI, or background service.
- Reports resource addresses and action names, not attribute diffs.
- Ignores data-source changes and `no-op` actions.
- A zero result is not proof that the environment matches configuration: it means the input recorded no findings in the selected section. Stale plans, skipped refreshes, targeted plans, provider behavior, and ignored attributes can all limit coverage.
- It does not detect unmanaged resources absent from Terraform state.
- It does not certify security or compliance.

## Reference

[Terraform JSON output format](https://developer.hashicorp.com/terraform/internals/json-format)

## License

MIT. Copyright (c) 2026 Juan M De Sousa.
