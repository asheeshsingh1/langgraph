### What is Agentic AI
Agentic Al is a type of Al that can take up a task or goal from a user and then work toward completing it on its own,
with minimal human guidance. It plans, takes action, adapts to changes, and seeks help only when necessary.

### Example for understanding use case of Agentic AI
Problem Statement: Hire a `Backend Engineer`
- `Solution 1:` Use Chat bot with AI capabilities
    - Problem is, it is reactive and not proactive.
- `Solution 2:` RAG based Chat bot
    - Better than previous one, as it would suggest solution based on you company docs but still reactive not proactive.
- `Solution 3:` Tool Augmented Chat bot
    - Better than previous one as you ask the chat bot to do stuff on your befalf, like it can post job on Linkedin etc but this is still reactive and not proactive.
- `Solution 4:` Agentic AI enabled Chat Bot
    - Best solution as of now, as you only need to define the problem statement rest of things would be taken care of by this chat bot with tools. All you need to do is just give approvals whenever it loops in the human for the same.

Solution 4 is proactive, has memory, can take action, can adapt and gives specific advice.

### Let's Deep dive solution 4 and look at key characterstics:
![alt text](./images/characterstics.png)
#### 1. Autonomy
Autonomy refers to the Al system's ability to make decisions and take actions on its own to achieve a given goal, without needing step-by-step human instructions.

1. Our Al recruiter is autonomous
2. It's proactive
3. Autonomy in multiple facets
    a. Execution
    b. Decision making
    c. Tool usage

4. Autonomy can be controlled

    a. Permission Scope - Limit what tools or actions the agent can perform independently. (Can screen candidates, but needs approval before rejecting anyone.)

    b. Human-in-the-Loop (HITL) - Insert checkpoints where human approval is required before continuing. (Can I post this JD)

    c. Override Controls - Allow users to stop, pause, or change the agent's behaviour at any time. (pause screening command to halt resume processing.)

    d. Guardrails / Policies - Define hard rules or ethical boundaries the agent must follow. (Never schedule interviews on weekends)

5. Autonomy can be dangerous

    a. The application autonomously sends out job offers with incorrect salaries or terms.

    b. The application shortlists candidates by age or nationality, violating anti-discrimination laws.

    c. The applications spending extra on Linkedin ads.

#### 2. Goal Oriented

Being goal-oriented means that the Al system operates with a persistent objective in mind and continuously directs its actions to achieve that objective, rather than just responding to isolated prompts.

1. Goals acts as a compass for Autonomy

2. Goals can come with constraints

3. Goals are stored in core memory

        {
            "main_goal": "Hire a backend engineer"
            "constraints": {
                "experience": "2-4 years",
                "remote": true,
                "stack": ["Python", "Django", "Cloud"]
            },
            "status": "active",
            "created_at": "2025-06-27",
            "progress": {
                "JD_created": true,
                "posted _on": ["LinkedIn", "Angellist"),
                "applications_received": 8,
                "interviews_scheduled": 2
            }
        }

4. Goals can be altered

#### 3. Planning
Planning is the agent's ability to break down a high-level goal into a structured sequence of actions or subgoals and decide the best path to achieve the desired outcome.

- Step 1: Generating multiple candidate plans
    * Plan A: Post JD on LinkedIn, GitHub Jobs, AngelList
    * Plan B: Use internal referrals and hiring agencies

- Step 2: Evaluate each plan
    * Efficiency (Which is faster?)
    * Tool Availability (Which tools are available)
    * Cost (Does it require premium tools?)
    * Risk (Will it fail if we get no applicants?)
    * Alignment with constraints (remote-only? budget?)

- Step 3: Select the best plan with the help of:

    * Human-in-the-loop input (e.g., "Which of these options do you prefer?")
    * A pre-programmed policy (e.g., "Favor low-cost channels first")

#### 4. Reasoning
Reasoning is the cognitive process through which an agentic ai system interprets information, draws conclusions, and makes decisions - both while planning ahead and while executing actions in real time.

Reasoning During Planning:

- `Goal decomposition:` Break down abstract goals into concrete steps
- `Tool selection:` Decide which tools will be needed for which steps
- `Resource estimation:` Estimate time, dependencies, risks

Reasoning During Execution:

- `Decision-making:` Choosing between options (3 candidates match → schedule 2 best, reject 1)
- `HITL handling:` Knowing when to pause and ask for help (Unsure about salary range)
- `Error handling:` Interpreting tool/API failures and recovering


#### 5. Adaptability
Adaptability is the agent's ability to modify its plans, strategies, or actions in response to unexpected conditions - all while staying aligned with the goal.
- Failures (Calendar API)
- External feedback (Less no of applications)
- Changing goals (Hiring a freelancer)


#### 6. Context Awareness
Context awareness is the agent's ability to understand, retain, and utilize relevant information from the ongoing task, past interactions, user preferences, and environmental cues to make better decisions throughout a multi-step process.

1. Types of context

    - The original goal
    - Progress till now + Interaction history (Job description was finalized and posted to LinkedIn &
    GitHub Jobs)
    - Environment state (Number of applicants so far = 8 or LinkedIn promotion ends in 2 days)
    - Tool responses (Resume parser → "Candidate B has 3 years Django + AWS experience or Calendar
    API > "No conflicts at 2 PM Wednesday)
    - User specific preferences (Prefers remote-first candidates or Likes receiving interview questions in a Google Doc)
    - Policy or Guardrails(Do not send offer without explicit user approval or Never use platforms that require paid ads unless approved)

2. Context awareness is implemented through memory
3. Short term memory
4. Long term memory

### Agentic AI core components:
![alt text](./images/components.png)

#### 1. Brain:

* `Goal Interpretation:` -> Understands user instructions and translates them into objectives.
* `Planning:` -> Breaks down high-level goals into subgoals and ordered steps.
* `Reasoning:` -> Makes decisions, resolves ambiguity, and evaluates trade-offs.
* `Tool Selection:` -> Chooses which tool(s) to use at a given step.
* `Communication:` -> Generates natural language outputs for humans or other agents.


#### 2. Orchestrator(Langraph):

* `Task Sequencing:` -> Determines the order of actions (step 1 → step 2 → ...).
* `Conditional Routing:` -> Directs flow based on context (e.g., if failure, retry or escalate).
* `Retry Logic:` -> Handles failed tool calls or reasoning attempts with backoff.
* `Looping & Iteration:` -> Repeats steps (e.g., keep checking job apps until 10 are received).
* `Delegation:` -> Decides whether to hand off work to tools, LLM, or human.


#### 3. Tools
* `External Actions:` -> Perform API calls (e.g., post a job, send an email, trigger onboarding).
* `Knowledge Base Access:` -> Retrieve factual or domain-specific information using RAG or search
tools to ground responses.

#### 4. Memory
* `Short-Term Memory:` -> Maintains the active session's context — recent user messages, tool calls, and immediate decisions.
* `Long-Term Memory:` -> Persists high-level goals, past interactions, user preferences, and decisions across sessions.
* `State Tracking:` -> Monitors progress: what's completed, what's pending (e.g., "JD posted", "Offer sent").

#### 5. Supervisor

* `Approval Requests (HITL):` -> Agent checks with human before high-risk actions (e.g., sending offers).
* `Guardrails Enforcement:` -> Blocks unsafe or non-compliant behavior.
* `Edge Case Escalation:` -> Alerts humans when uncertainty/conflict arises.