test_that("pipeline_comparison_dashboard aggregates participant-session QC rows", {
  x <- data.frame(
    participant_id = c("P01", "P01", "P02", "P02"),
    session = c("S1", "S1", "S1", "S2"),
    missing_rate = c(0.10, 0.20, 0.05, 0.40),
    quality_index = c(0.90, 0.80, 0.95, 0.50),
    qc_status = c("accept", "accept", "accept", "review"),
    failed_rules = c("", "", "", "high_missingness"),
    excluded = c(FALSE, FALSE, FALSE, TRUE),
    audit_notes = c("", "", "", "Sparse signal"),
    stringsAsFactors = FALSE
  )

  out <- pipeline_comparison_dashboard(x)

  expect_s3_class(out, "gazepoint_pipeline_comparison_dashboard")
  expect_equal(out$overall$n_groups, 3)
  expect_equal(out$overall$n_rows, 4)
  expect_equal(out$overall$n_issue_groups, 1)
  expect_equal(out$overall$n_excluded_rows, 1)
  expect_equal(nrow(out$issues), 1)
  expect_true("high_missingness" %in% out$issues$failed_rules)
})

test_that("pipeline_comparison_dashboard works with explicit grouping columns", {
  x <- data.frame(
    file_id = c("a", "a", "b"),
    prop_missing = c(0.1, 0.2, 0.3),
    signal_quality = c(0.8, 0.7, 0.6),
    stringsAsFactors = FALSE
  )

  out <- pipeline_comparison_dashboard(x, grouping_cols = "file_id")

  expect_s3_class(out, "gazepoint_pipeline_comparison_dashboard")
  expect_equal(out$overall$n_groups, 2)
  expect_equal(out$dashboard$n_rows[out$dashboard$file_id == "a"], 2)
})

test_that("pipeline_comparison_dashboard validates inputs", {
  expect_error(pipeline_comparison_dashboard(1:3), "data frame")
  expect_error(pipeline_comparison_dashboard(data.frame()), "at least one row")
  expect_error(
    pipeline_comparison_dashboard(data.frame(x = 1), grouping_cols = "missing_col"),
    "Grouping columns not found"
  )
})
