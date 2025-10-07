# AutoOrganizer Architecture Notes

## Planner / Mover / Logger Interaction

```mermaid
sequenceDiagram
    participant CLI
    participant Planner
    participant Scanner
    participant SystemFilter
    participant Classifier
    participant Mover
    participant Logger

    CLI->>Planner: build_plan(sources, dst)
    Planner->>Scanner: scan(sources)
    Scanner-->>Planner: candidates
    Planner->>SystemFilter: evaluate(candidate)
    SystemFilter-->>Planner: decision
    Planner->>Classifier: classify(candidate)
    Classifier-->>Planner: category/confidence
    Planner-->>CLI: plan.json + report

    CLI->>Mover: execute_plan(plan.items)
    Mover->>Logger: log_event(move.start)
    Mover->>Mover: rename/copy+verify
    Mover->>Logger: log_event(move.done)
    Mover-->>CLI: ExecutionSummary + rollback.json
```

The planner orchestrates scanning, filtering, and classification to produce a `plan.json`
without touching the file system. When executing `run --plan`, the mover performs atomic
renames on the same volume and safe copy+verify sequences across volumes. Every significant
step emits structured JSON lines via the logger, which handles log rotation, home directory
redaction, and log level control.
