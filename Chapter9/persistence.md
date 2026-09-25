## Persistence

Persistence in LangGraph refers to the ability to **save and restore the state of a workflow over time**.

It allows a LangGraph application to maintain state across multiple interactions, resume interrupted workflows, support human intervention, and inspect previous states of a workflow.

### Checkpointers in Persistence

A **checkpointer** is responsible for saving the state of a LangGraph workflow at specific points during execution.

Whenever a graph reaches a checkpoint, the current state is persisted. This allows the workflow to later resume from that state instead of starting from the beginning.

Conceptually:

```text
Graph Execution
      |
      v
   Node A
      |
      v
  Checkpoint
      |
      v
   Node B
      |
      v
  Checkpoint
      |
      v
   Node C
```

LangGraph provides different checkpointer implementations depending on the persistence requirements, such as in-memory or database-backed persistence.

Example:

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

graph = builder.compile(
    checkpointer=checkpointer
)
```

The checkpointer stores information such as:

* Graph state
* Execution progress
* Messages
* Previous checkpoints
* Metadata associated with the execution

---

### Threads in Persistence

A **thread** represents a unique execution or conversation of a LangGraph workflow.

A `thread_id` is used to associate checkpoints with a particular workflow execution.

For example:

```python
config = {
    "configurable": {
        "thread_id": "user-123"
    }
}
```

When the graph is invoked with the same `thread_id`, LangGraph can retrieve the persisted state associated with that thread.

```text
Thread: user-123

        ┌──────────────┐
        │   Request 1  │
        └──────┬───────┘
               ↓
         Checkpoint 1
               ↓
        ┌──────────────┐
        │   Request 2  │
        └──────┬───────┘
               ↓
         Checkpoint 2
               ↓
        ┌──────────────┐
        │   Request 3  │
        └──────────────┘
```

Different users or conversations can have separate threads:

```text
thread_id = user-123
thread_id = user-456
thread_id = conversation-789
```

This makes threads particularly useful for **multi-user applications and conversational agents**.

---

## Benefits of Persistence

### 1. Short-Term Memory

Persistence allows a workflow to remember previous interactions within a thread.

For example:

```text
User: My name is Asheesh.
       ↓
   Checkpoint
       ↓
User: What is my name?
       ↓
LangGraph retrieves previous state
       ↓
Assistant: Your name is Asheesh.
```

This provides **short-term conversational memory** without requiring the workflow to start from an empty state every time.

> Persistence is not the same as long-term memory. Persistence stores the state of workflow execution, while long-term memory typically stores information that should survive across different threads or conversations.

---

### 2. Fault Tolerance

Persistence allows a workflow to **recover from failures or interruptions**.

Without persistence:

```text
Node A → Node B → Node C → FAILURE
                         ↓
                    Start again
```

With persistence:

```text
Node A → Checkpoint → Node B → Checkpoint → Node C → FAILURE
                                  ↓
                              Resume here
```

The workflow can resume from the most recent checkpoint instead of repeating the entire execution.

This is particularly useful for:

* Long-running workflows
* Expensive LLM calls
* External API calls
* Background jobs
* Multi-step agents

---

### 3. Human-in-the-Loop

Persistence enables a workflow to **pause, wait for human input, and resume later**.

For example:

```text
Agent analyzes request
        ↓
   Human approval
        ↓
      PAUSE
        ↓
   Checkpoint
        ↓
Human provides approval
        ↓
      RESUME
        ↓
Continue workflow
```

The workflow state is persisted while waiting for the human.

This is useful for workflows involving:

* Approval processes
* Code deployment
* Financial transactions
* Content moderation
* Tool execution
* Sensitive actions

---

### 4. Time Travel

Because LangGraph stores multiple checkpoints, it is possible to inspect or replay previous states of a workflow.

For example:

```text
Checkpoint 1
     ↓
Checkpoint 2
     ↓
Checkpoint 3
     ↓
Checkpoint 4
```

You can inspect the state at an earlier checkpoint and potentially **resume execution from that point with a different path**.

This is useful for:

* Debugging workflows
* Understanding agent decisions
* Replaying executions
* Testing alternative outcomes
* Investigating failures

Conceptually:

```text
                 ┌──→ Path A
Checkpoint 2 ────┤
                 └──→ Path B
```

Instead of modifying the original execution, a new execution can be created from a previous state.

---

### 5. Stateful Workflows

Persistence allows LangGraph to maintain state across multiple invocations.

Without persistence:

```text
Request 1 → State lost
Request 2 → New state
Request 3 → New state
```

With persistence:

```text
Request 1
    ↓
Checkpoint
    ↓
Request 2
    ↓
Checkpoint
    ↓
Request 3
```

This makes it possible to build workflows that run over minutes, hours, or even days.

---

### 6. Debugging and Observability

Persisted checkpoints provide a history of how the workflow evolved.

You can inspect:

* What the state looked like
* Which nodes executed
* What messages were generated
* Where the workflow stopped
* How the state changed between steps

This makes debugging complex agentic workflows much easier.

---

## Persistence Architecture

A simplified LangGraph persistence architecture looks like this:

```text
                  ┌─────────────────┐
                  │   User Request  │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │    LangGraph    │
                  │    Workflow     │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │     Node A      │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │   Checkpointer  │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │     Node B      │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │   Checkpointer  │
                  └────────┬────────┘
                           ↓
                  ┌─────────────────┐
                  │     Node C      │
                  └─────────────────┘

                         ↕
                ┌──────────────────┐
                │ Persistent Store │
                │                  │
                │ State            │
                │ Checkpoints      │
                │ Thread Metadata  │
                └──────────────────┘
```

The key relationship is:

```text
Thread
  ↓
Checkpoints
  ↓
Workflow State
```

---

## Persistence vs Memory

It is important to distinguish **persistence** from **memory**.

| Concept           | Purpose                                                 |
| ----------------- | ------------------------------------------------------- |
| Persistence       | Saves workflow state and checkpoints                    |
| Thread            | Identifies a specific workflow execution/conversation   |
| Checkpoint        | Snapshot of workflow state at a point in execution      |
| Short-term memory | State available within a conversation/thread            |
| Long-term memory  | Information intentionally retained across conversations |

For example:

```text
                    Persistence
                         │
             ┌───────────┴───────────┐
             ↓                       ↓
        Checkpoints              Threads
             │                       │
             ↓                       ↓
      Workflow State         Conversation State
             │
             ↓
       Short-Term Memory
```

---

## Key Takeaway

**Persistence makes LangGraph workflows durable and stateful.**

The main components are:

* **Checkpointer** → Saves workflow state at checkpoints.
* **Thread** → Identifies a specific workflow execution or conversation.
* **State** → Contains the data required to continue the workflow.
* **Persistence** → Allows the state to survive across invocations and interruptions.

This enables important capabilities such as:

* Short-term memory
* Fault tolerance
* Human-in-the-loop workflows
* Time travel
* Stateful and long-running workflows
* Debugging and replay
