# Test for Claim 4: Leadership Constraints on Relation App Databag Writes

## Claim Statement

> Writing to application relation databag is leader-only; non-leader attempts fail with an exception due to permission checks.

## Why This Claim Matters

Relation data is central to charm integrations. App-level databag writes are particularly critical because they hold shared state that all units of an application should be aware of. If leadership constraints are misunderstood:

- **Silent failures**: Non-leader units might crash handlers or skip updates, causing inconsistent relation state
- **Production outages**: Charms that work in same-model testing could fail in multi-unit deployments
- **Resource leaks**: Incorrect assumptions about who can clean up shared resources on relation-broken

## Test Design Philosophy

The test is designed to be **low-abstraction** and **human-reviewable**:

1. **Explicit charm roles**: Two separate, simple charms (provider and requirer) with clear responsibilities
2. **Minimal logic**: Each charm does one thing—attempt to write app databag and log the outcome
3. **Real deployment**: Uses actual Juju deployment with multi-unit scenarios (not mocks)
4. **Log-based validation**: Verifies claims by reading what charms actually did, not by mocking framework calls
5. **Leadership tests**: Validates both steady-state leadership and leadership transfer scenarios

## Test Assets

### Charm 1: `relation-app-write-provider`

**Purpose**: Provides a test relation and attempts app databag writes in relation events.

**Key Behavior**:
- Observes `relation-created` and `relation-joined` events
- Logs whether unit is leader: `is_leader=True` or `is_leader=False`
- Attempts to write to `event.relation.data[self.app]["key"] = value`
- Logs success: `"Successfully wrote to app databag"`
- Logs failure: `"Failed to write app databag: [exception]"`

**Relation Interface**: `test-app-write` (provider side)

### Charm 2: `relation-app-write-requirer`

**Purpose**: Requires the same test relation and also attempts app databag writes.

**Key Behavior**:
- Identical structure to provider, but on requirer side
- Observes same relation events
- Attempts same writes with different key names (to distinguish provider vs requirer writes)
- Logs same success/failure patterns

**Relation Interface**: `test-app-write` (requirer side)

## Test Scenarios

### Scenario 1: Multi-Unit Leadership (Main Test)

**Deployment**:
```
provider: 2+ units (1 leader, 1+ non-leader)
requirer: 1 unit
```

**Steps**:
1. Deploy provider with 2 units
2. Deploy requirer with 1 unit
3. Integrate: `provider:test-app-write` ↔ `requirer:test-app-write`
4. Wait for relation events to fire (relation-created, relation-joined)
5. Collect charm logs from all units

**Validation**:
```
✓ Leader unit(s) log: "Successfully wrote to app databag"
✓ Non-leader unit(s) log: "Failed to write app databag: ops.ModelError"
✓ Exception type is ModelError (not AttributeError, PermissionError, etc.)
```

**Key Assertions**:
- At least one non-leader exists (otherwise test is meaningless)
- Leader write succeeds
- All non-leader writes fail with ModelError
- Exception message indicates permission/leadership issue

### Scenario 2: Leadership Transfer (Secondary Test)

**Prerequisite**: Provider has 2+ units from Scenario 1

**Steps**:
1. Identify current leader unit
2. Remove the current leader unit: `juju remove-unit provider/0`
3. Juju promotes next unit to leader
4. Verify new leader is different from old leader
5. Check logs for updated leadership state

**Validation**:
```
✓ New leader is different from old leader
✓ (If relation events re-fire) New leader can write, old leader cannot
```

**Purpose**: Ensures leadership changes are respected and permissions update correctly.

## How to Understand the Test Code

### Integration Test Structure

**File**: `charms/relation-app-write-provider/tests/integration/test_charm.py`

Three main test functions:

1. **`test_deploy_provider_multi_unit`**
   - Deploys provider charm with 2 units
   - Verifies deployment succeeds and all units reach `active` state
   - Sets baseline for subsequent tests

2. **`test_relation_app_write_leader_only`** ⭐ MAIN TEST
   - Deploys requirer charm
   - Integrates the two charms
   - Collects logs and determines leadership per unit
   - **Core validation**: Leader succeeds, non-leaders fail with ModelError
   - Assertions make claim 4 falsifiable:
     - If this test fails, the claim is disproven
     - If this test passes, the claim is supported by real-world evidence

3. **`test_leadership_change_write_permissions`**
   - Removes current leader to force transfer
   - Verifies new leader differs from old
   - Demonstrates leadership changes affect permissions

### Key Helper Functions

**`_get_unit_logs(juju, unit_name)`**
- Uses `juju debug-log` to retrieve unit logs
- Real charm output, not mocked
- Allows assertions on actual charm behavior

**`_check_write_success(juju, unit_name)`**
- Searches logs for success message
- Returns `True` if leader successfully wrote
- Returns `False` if non-leader failed or not found

**`_relation_hooks_fired(status, app_name)`**
- Waits for relation events to complete
- Simple heuristic: units reach `active` status

## Running the Test Locally

### Prerequisites
```bash
# Install charmcraft and Juju
sudo snap install charmcraft --classic
sudo snap install juju --classic

# Or use Concierge (as in CI):
sudo snap install --classic concierge
sudo concierge prepare -p machine
```

### Manual Steps

```bash
# Pack provider charm
cd charms/relation-app-write-provider
charmcraft pack

# Pack requirer charm
cd ../relation-app-write-requirer
charmcraft pack

# Run integration tests
cd ../relation-app-write-provider
CHARM_PATH="$(pwd)/relation-app-write-provider*.charm" \
REQUIRER_CHARM_PATH="$(cd ../relation-app-write-requirer && pwd)/relation-app-write-requirer*.charm" \
tox -e integration -- --juju-dump-logs logs
```

### Interpreting Results

**Success** ✅
```
test_deploy_provider_multi_unit PASSED
test_relation_app_write_leader_only PASSED
test_leadership_change_write_permissions PASSED
```

**Failure** ❌
- If non-leader write succeeded → claim is false
- If leader write failed → claim is incomplete/incorrect
- If exception type is wrong → claim needs refinement

## What This Test Does NOT Test

- **Unit databag writes**: Test only validates app-level writes
- **Peer relations**: Test uses provider/requirer, not peer relations
- **Subordinate relations**: Different scoping rules, not covered here
- **Cross-model relations**: Test runs in single model only

## Design Rationale: Why This Approach?

### Why real Juju deployment, not mocks?
- Leadership is enforced by Juju, not by ops library
- Real exception types and messages matter
- Logs are auditable by human reviewers
- Demonstrates real-world behavior, not theoretical

### Why log-based validation?
- No need to modify charms to emit assertions
- Charms remain realistic and simple
- Logs are human-readable and inspectable
- Easy to add new checks by searching for new log patterns

### Why two separate charms?
- Demonstrates integration behavior (not unit-level testing)
- Provider and requirer may have different constraints
- Realistic scenario matching real charm relationships
- Clearer signal about what is being tested

### Why multi-unit?
- Single-unit deployments always have a leader
- Multi-unit deployments reveal permission enforcement
- Real-world charms often use multiple units
- Tests the scaling dimension of the claim

## Potential Issues and Mitigations

| Issue | Mitigation |
|-------|-----------|
| Logs are lost or unreadable | Use `juju debug-log` with explicit filters; upload logs as CI artifacts |
| Leadership detection is unreliable | Charm logs its leadership state explicitly in every event |
| Events don't fire | Wait for units to reach `active` before checking; use explicit waits |
| Timing issues | Use `juju wait` with generous timeouts; idempotent event handlers |
| Flakiness in leadership transfer | Run multiple times; ensure units reach stable state before assertion |

## Future Enhancements

1. **Test peer relations**: Create a third charm variant with peer relations
2. **Test leadership failover scenarios**: Simulate network partitions
3. **Test subordinate relations**: Add scope=container variant
4. **Detailed assertion logging**: Log expected vs actual per unit for easier debugging
5. **Compare exception types**: Verify ops.ModelError specifically (not generic Exception)

## References

- [Ops Library: Relation](https://ops.readthedocs.io/en/latest/reference/ops.Relation.html)
- [Ops Library: RelationCreatedEvent](https://ops.readthedocs.io/en/latest/reference/ops.RelationCreatedEvent.html)
- [Juju Relations Documentation](https://juju.is/docs/juju/relations)
- [Charm Leadership](https://juju.is/docs/juju/leadership)
- [Integration Testing Guide](https://ops.readthedocs.io/en/latest/howto/write-integration-tests/)
