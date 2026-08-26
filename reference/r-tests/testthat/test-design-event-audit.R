test_that("audit_gazepoint_experiment_design summarises balanced designs", {
  dat <- data.frame(
    participant = rep(paste0("P", 1:4), each = 4),
    trial = rep(1:4, times = 4),
    condition = rep(c("A", "B"), times = 8),
    session = rep(c("S1", "S2"), each = 8),
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition",
    session_col = "session",
    expected_conditions = c("A", "B"),
    min_trials_per_condition = 1
  )

  expect_s3_class(audit, "gazepoint_experiment_design_audit")
  expect_true(is.data.frame(audit$overview))
  expect_true(is.data.frame(audit$participant_summary))
  expect_true(is.data.frame(audit$condition_summary))
  expect_true(is.data.frame(audit$participant_condition_counts))
  expect_true(is.data.frame(audit$warnings))

  expect_equal(audit$overview$n_participants, 4L)
  expect_equal(audit$overview$n_conditions, 2L)
  expect_true(audit$overview$has_trial_column)
  expect_true(audit$overview$has_condition_column)
  expect_true(audit$overview$has_session_column)
  expect_equal(NROW(audit$warnings), 0L)
})

test_that("audit_gazepoint_experiment_design flags missing expected conditions and low cells", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2"),
    trial = c(1, 2, 1),
    condition = c("A", "A", "A"),
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition",
    expected_conditions = c("A", "B"),
    min_trials_per_condition = 1
  )

  expect_s3_class(audit, "gazepoint_experiment_design_audit")
  expect_true(any(audit$warnings$issue == "missing_expected_conditions"))
  expect_true(any(audit$warnings$issue == "low_participant_condition_cells"))
})

test_that("audit_gazepoint_event_coverage summarises complete event coverage", {
  dat <- expand.grid(
    participant = paste0("P", 1:3),
    trial = 1:2,
    event = c("stimulus", "response"),
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response")
  )

  expect_s3_class(audit, "gazepoint_event_coverage_audit")
  expect_equal(audit$overview$n_units, 6L)
  expect_equal(audit$overview$n_expected_events, 2L)
  expect_equal(audit$overview$n_complete_units, 6L)
  expect_equal(audit$overview$complete_unit_prop, 1)
  expect_equal(NROW(audit$warnings), 0L)
  expect_true(all(audit$event_summary$coverage_prop == 1))
})

test_that("audit_gazepoint_event_coverage flags incomplete event coverage", {
  dat <- data.frame(
    participant = c("P1", "P1", "P2"),
    trial = c(1, 1, 1),
    event = c("stimulus", "response", "stimulus"),
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response", "feedback")
  )

  expect_s3_class(audit, "gazepoint_event_coverage_audit")
  expect_true(any(audit$warnings$issue == "events_never_observed"))
  expect_true(any(audit$warnings$issue == "partial_event_coverage"))
  expect_true(any(audit$warnings$issue == "incomplete_event_units"))
})

test_that("audit_gazepoint_event_coverage supports all-row coverage", {
  dat <- data.frame(
    event = c("stimulus", "response", "feedback"),
    value = 1:3,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    expected_events = c("stimulus", "response", "feedback")
  )

  expect_s3_class(audit, "gazepoint_event_coverage_audit")
  expect_equal(audit$overview$n_units, 1L)
  expect_equal(audit$overview$n_complete_units, 1L)
  expect_equal(audit$overview$complete_unit_prop, 1)
})

test_that("audit_gazepoint_condition_balance summarises balanced condition grids", {
  dat <- expand.grid(
    participant = paste0("P", 1:4),
    condition = c("A", "B"),
    trial = 1:3,
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_condition_balance(
    dat,
    participant_col = "participant",
    condition_col = "condition",
    trial_col = "trial",
    expected_conditions = c("A", "B")
  )

  expect_s3_class(audit, "gazepoint_condition_balance_audit")
  expect_equal(audit$overview$n_participants, 4L)
  expect_equal(audit$overview$n_conditions, 2L)
  expect_equal(audit$overview$n_trials, 24L)
  expect_equal(audit$overview$trial_imbalance_ratio, 1)
  expect_true(audit$overview$complete_participant_condition_grid)
  expect_equal(NROW(audit$warnings), 0L)
})

test_that("audit_gazepoint_condition_balance flags missing cells and imbalance", {
  dat <- data.frame(
    participant = c(rep("P1", 10), rep("P2", 2), rep("P3", 2)),
    condition = c(rep("A", 10), rep("A", 2), rep("B", 2)),
    trial = seq_len(14),
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_condition_balance(
    dat,
    participant_col = "participant",
    condition_col = "condition",
    trial_col = "trial",
    expected_conditions = c("A", "B")
  )

  expect_s3_class(audit, "gazepoint_condition_balance_audit")
  expect_true(any(audit$warnings$issue == "missing_participant_condition_cells"))
  expect_true(any(audit$warnings$issue == "condition_trial_imbalance"))
  expect_true(any(audit$warnings$issue == "incomplete_participant_condition_grid"))
})

test_that("plot_gazepoint_design_coverage returns ggplot objects", {
  skip_if_not_installed("ggplot2")

  dat <- expand.grid(
    participant = paste0("P", 1:3),
    condition = c("A", "B"),
    trial = 1:2,
    stringsAsFactors = FALSE
  )

  dat$event <- rep(c("stimulus", "response"), length.out = NROW(dat))

  design_audit <- audit_gazepoint_experiment_design(
    dat,
    participant_col = "participant",
    trial_col = "trial",
    condition_col = "condition",
    expected_conditions = c("A", "B")
  )

  event_audit <- audit_gazepoint_event_coverage(
    dat,
    event_col = "event",
    participant_col = "participant",
    trial_col = "trial",
    expected_events = c("stimulus", "response")
  )

  balance_audit <- audit_gazepoint_condition_balance(
    dat,
    participant_col = "participant",
    condition_col = "condition",
    trial_col = "trial",
    expected_conditions = c("A", "B")
  )

  expect_s3_class(
    plot_gazepoint_design_coverage(design_audit, type = "condition_counts"),
    "ggplot"
  )

  expect_s3_class(
    plot_gazepoint_design_coverage(design_audit, type = "participant_trials"),
    "ggplot"
  )

  expect_s3_class(
    plot_gazepoint_design_coverage(event_audit, type = "event_coverage"),
    "ggplot"
  )

  expect_s3_class(
    plot_gazepoint_design_coverage(balance_audit, type = "warnings"),
    "ggplot"
  )
})

test_that("design and event audit functions validate inputs", {
  dat <- data.frame(
    participant = "P1",
    trial = 1,
    condition = "A",
    event = "stimulus"
  )

  expect_error(
    audit_gazepoint_experiment_design(
      data.frame(),
      participant_col = "participant"
    ),
    "at least one row"
  )

  expect_error(
    audit_gazepoint_experiment_design(
      dat,
      participant_col = "missing"
    ),
    "was not found"
  )

  expect_error(
    audit_gazepoint_event_coverage(
      dat,
      event_col = "missing"
    ),
    "was not found"
  )

  expect_error(
    audit_gazepoint_condition_balance(
      dat,
      participant_col = "participant",
      condition_col = "missing"
    ),
    "was not found"
  )

  expect_error(
    audit_gazepoint_event_coverage(
      dat,
      event_col = "event",
      unit_cols = "missing"
    ),
    "missing column"
  )

  expect_error(
    audit_gazepoint_experiment_design(
      dat,
      participant_col = "participant",
      expected_conditions = c("A", "")
    ),
    "expected_conditions"
  )
})
