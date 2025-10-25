# Optimization Requirements

## Objective
The goal of the optimization is to determine the fastest route for the transporter(s) to transport batch(es) according to their respective processing programs. Each batch's processing steps must be executed in the specified order.

## Constraints
1. **Processing Step Timing**:
   - The minimum time for each processing step must not be violated.
   - The maximum time for each processing step must not be exceeded.

2. **Transporter Movement Timing**:
   - Transporter movement times must adhere to pre-calculated durations based on a physics function.
   - A batch transfer consists of:
     - Lift time
     - Travel time between stations
     - Lowering time

3. **Sequential Tasks**:
   - There must be sufficient time between two consecutive tasks for the transporter to move from the end of the previous task to the start of the next task.

4. **Non-Overlapping Tasks**:
   - The transporter cannot have overlapping tasks or movements.

## Flexibility
- The processing time for each step can vary freely within the defined minimum and maximum time limits.
