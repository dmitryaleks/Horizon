# The context and targets

We are building a Monte Carlo based estimation engine that offers estimates for new tasks based on a database of past
estimates and actual effort for various tasks performed by the same team.

# Inputs

The past data will be stored in JSON files (the format is to be design part of this project).

Available information is as follows:

  - the name of the original task;
  - the number of story points (in Jira terms) associated with the task;
  - the original estimate in man days;
  - the actual observed number of man days for the task;
  - the distance in calendar days b/w the beginning of the work and the end of the work for a given task in the past.

# Querying

When being queried the following information is offered:

  - the name of the task;
  - the number of story points estimated by the same team as the past data comes from;
  - the rough pre-estimate from the same team.
 
# The estimation process

A Monte Carlo trial that tries to model hundreds or more future paths based on existing data and the inputs to ultimately
come up with estimates and confidence intervals for them. TODO: research and refind the exact methodology.

# Output

A report with an HTML dashboard presenting:

  - refined estimates along with confidence intervals (as a table and as an interactive statistical chart with visually expressed confidence interval);
  - the same estimates expressed in a "Three-point estimation" estimates methodology as a table;
  - estimate of calendar delivery from day one to last day (E.g. 80 calendar days);
  - reference cases from past data available as a table.