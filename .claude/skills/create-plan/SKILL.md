---
name: create-plan
description: Create a Plan.md file for complex multi-step tasks. Use when user says "create plan", "plan this", "break down task", "how to approach", or when a task requires multiple steps.
---

# Create Plan Skill

## Purpose
Break down complex tasks into actionable plans with checkboxes, stored in `/Plans/` folder for tracking.

## When to Use
- Multi-step tasks
- Projects requiring coordination
- Tasks spanning multiple days
- When user asks "how should I approach this?"

## Workflow

1. **Analyze the task** - Understand scope and requirements
2. **Break into steps** - Create logical sub-tasks
3. **Assign priorities** - P1/P2/P3 for each step
4. **Estimate effort** - Simple/Medium/Complex
5. **Create Plan.md file** - Save to `/Plans/` folder
6. **Create action items** - Optional: create files in `/Needs_Action/`

## Plan.md Template

```markdown
---
type: plan
created: [timestamp]
status: active
project: [project name]
priority: [P1/P2/P3]
estimated_effort: [simple/medium/complex]
---

# Plan: [Task Title]

## Objective
[Clear description of what needs to be accomplished]

## Context
[Background information, constraints, dependencies]

## Steps

### Phase 1: [Phase Name]
- [ ] Step 1.1: [Description] (Priority: P1)
- [ ] Step 1.2: [Description] (Priority: P2)

### Phase 2: [Phase Name]
- [ ] Step 2.1: [Description]
- [ ] Step 2.2: [Description]

### Phase 3: [Phase Name]
- [ ] Step 3.1: [Description]

## Dependencies
- [External dependency 1]
- [External dependency 2]

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk 1] | High/Medium/Low | [How to handle] |

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Notes
[Additional context or considerations]

---
*Plan created by AI Employee: [timestamp]*
```

## Creating a Plan

### Step 1: Gather Information
Ask user for:
- What is the goal?
- Any constraints or deadlines?
- Dependencies on other tasks?

### Step 2: Create Plan File
Save to: `/AI_Employee_Vault/Plans/PLAN_[name]_[date].md`

### Step 3: Optional - Create Action Items
For immediate steps, create files in `/Needs_Action/`:
```
/Needs_Action/TASK_[plan_name]_step1.md
/Needs_Action/TASK_[plan_name]_step2.md
```

## Plan Status Tracking

Update plan status as work progresses:
- `status: active` - Currently working
- `status: blocked` - Waiting on dependency
- `status: completed` - All steps done
- `status: cancelled` - No longer needed

## Example Plans

### Simple Plan (1-3 steps)
```markdown
# Plan: Reply to Client Email

## Steps
- [ ] Read full email thread
- [ ] Draft response
- [ ] Send (requires approval)
```

### Complex Plan (Multiple phases)
```markdown
# Plan: Launch New Product Feature

## Phase 1: Research
- [ ] Analyze competitor features
- [ ] Survey customer needs

## Phase 2: Design
- [ ] Create wireframes
- [ ] Review with team

## Phase 3: Implementation
- [ ] Develop feature
- [ ] Write tests
- [ ] Deploy to staging

## Phase 4: Launch
- [ ] Final QA
- [ ] Production deploy
- [ ] Announce to customers
```

## Integration with Other Skills

After creating plan:
- Use `update-dashboard` to reflect new plan
- Use `complete-task` when steps are done
- Plans link to action items in `/Needs_Action/`
