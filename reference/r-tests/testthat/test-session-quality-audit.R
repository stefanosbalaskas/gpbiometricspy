test_that("compute_gazepoint_quality_index combines metrics transparently", {
  qc <- data.frame(
    participant = c("P01", "P02", "P03"),
    missing_prop = c(0, 5, 10),
    signal_quality = c(10, 20, 30),
    constant_metric = c(4, 4, 4)
  )

  out <- compute_gazepoint_quality_index(
    qc,
    metric_cols = c("missing_prop", "signal_quality"),
    directions = c(signal_quality = "higher", missing_prop = "lower"),
    weights = c(signal_quality = 2, missing_prop = 1),
    index_col = "q"
  )

  expect_s3_class(out, "gazepoint_quality_index")
  expect_true(all(c(
    "quality_component_missing_prop",
    "quality_component_signal_quality",
    "q"
  ) %in% names(out)))

  expect_equal(round(out$q, 6), round(c(1 / 3, 1 / 2, 2 / 3), 6))

  params <- attr(out, "quality_index_parameters")
  expect_equal(params$directions[["missing_prop"]], "lower")
  expect_equal(params$directions[["signal_quality"]], "higher")
  expect_equal(params$weights[["missing_prop"]], 1)
  expect_equal(params$weights[["signal_quality"]], 2)

  constant <- compute_gazepoint_quality_index(qc, metric_cols = "constant_metric")
  expect_equal(constant$quality_index, rep(0.5, 3))
})

test_that("compute_gazepoint_quality_index handles missing values", {
  qc <- data.frame(
    participant = c("P01", "P02", "P03"),
    missing_prop = c(0.1, NA, 0.3),
    signal_quality = c(0.9, 0.8, NA)
  )

  out <- compute_gazepoint_quality_index(
    qc,
    metric_cols = c("missing_prop", "signal_quality"),
    directions = c("lower", "higher")
  )

  expect_s3_class(out, "gazepoint_quality_index")
  expect_true(all(is.finite(out$quality_index)))
})

test_that("audit_gazepoint_session_comparability flags unusual sessions", {
  qc <- data.frame(
    participant = rep(c("P01", "P02", "P03", "P04"), each = 2),
    session = rep(c("S1", "S2"), times = 4),
    prop_missing = c(0.02, 0.04, 0.03, 0.05, 0.25, 0.28, 0.01, 0.02),
    n_flags = c(1, 2, 1, 3, 12, 14, 0, 1),
    signal_quality = c(0.95, 0.92, 0.90, 0.88, 0.45, 0.40, 0.98, 0.96)
  )

  qi <- compute_gazepoint_quality_index(
    qc,
    metric_cols = c("prop_missing", "n_flags", "signal_quality"),
    directions = c(prop_missing = "lower", n_flags = "lower", signal_quality = "higher"),
    weights = c(prop_missing = 2, n_flags = 1, signal_quality = 2)
  )

  audit <- audit_gazepoint_session_comparability(
    qi,
    group_cols = c("participant", "session"),
    metric_cols = c("prop_missing", "n_flags", "quality_index"),
    method = "both",
    z_threshold = 1.5,
    iqr_multiplier = 1.5
  )

  expect_s3_class(audit, "gazepoint_session_comparability_audit")
  expect_named(audit, c("data", "flags", "summary", "parameters"))
  expect_equal(nrow(audit$data), 8)
  expect_equal(nrow(audit$flags), 24)
  expect_equal(nrow(audit$summary), 8)

  p03 <- audit$summary[audit$summary$participant == "P03", ]
  expect_equal(p03$n_flagged_metrics, c(3, 3))
  expect_equal(p03$prop_flagged_metrics, c(1, 1))

  non_p03 <- audit$summary[audit$summary$participant != "P03", ]
  expect_true(all(non_p03$n_flagged_metrics == 0))
})

test_that("audit_gazepoint_session_comparability handles missing metrics", {
  qc <- data.frame(
    participant = c("P01", "P02", "P03"),
    session = "S1",
    prop_missing = c(0.01, NA, 0.03)
  )

  audit <- audit_gazepoint_session_comparability(
    qc,
    group_cols = c("participant", "session"),
    metric_cols = "prop_missing"
  )

  p02_flags <- audit$flags[audit$flags$participant == "P02", ]
  expect_true(p02_flags$metric_missing)
  expect_true(p02_flags$any_flag)
  expect_equal(p02_flags$flag_reason, "metric_missing")

  p02_summary <- audit$summary[audit$summary$participant == "P02", ]
  expect_equal(p02_summary$n_missing_metrics, 1)
  expect_equal(p02_summary$n_flagged_metrics, 1)
})

test_that("summarize_gazepoint_qc_overview summarizes flags and metrics", {
  qc <- data.frame(
    participant = c("P01", "P01", "P02", "P02"),
    any_flag = c(TRUE, FALSE, TRUE, TRUE),
    missing_flag = c(FALSE, FALSE, TRUE, FALSE),
    quality_index = c(0.9, 0.8, 0.4, 0.5),
    prop_missing = c(0.02, 0.03, 0.20, 0.25)
  )

  overview <- summarize_gazepoint_qc_overview(
    qc,
    group_cols = "participant",
    quality_index_col = "quality_index",
    flag_cols = c("any_flag", "missing_flag"),
    metric_cols = "prop_missing"
  )

  expect_s3_class(overview, "gazepoint_qc_overview")
  expect_equal(nrow(overview), 2)

  p01 <- overview[overview$participant == "P01", ]
  p02 <- overview[overview$participant == "P02", ]

  expect_equal(p01$n_rows, 2)
  expect_equal(p01$n_any_flag, 1)
  expect_equal(p01$n_missing_flag, 0)
  expect_equal(p01$n_flagged_rows, 1)
  expect_equal(p01$prop_flagged_rows, 0.5)
  expect_equal(p01$quality_index_mean, 0.85)
  expect_equal(p01$prop_missing_mean, 0.025)

  expect_equal(p02$n_any_flag, 2)
  expect_equal(p02$n_missing_flag, 1)
  expect_equal(p02$n_flagged_rows, 2)
  expect_equal(p02$prop_flagged_rows, 1)
  expect_equal(p02$quality_index_min, 0.4)
})

test_that("summarize_gazepoint_qc_overview auto-detects logical flag columns", {
  qc <- data.frame(
    participant = c("P01", "P01", "P02"),
    dropout_flag = c(FALSE, TRUE, TRUE),
    other_value = c(1, 2, 3)
  )

  overview <- summarize_gazepoint_qc_overview(qc, group_cols = "participant")

  expect_true("n_dropout_flag" %in% names(overview))
  expect_equal(overview$n_dropout_flag[overview$participant == "P01"], 1)
  expect_equal(overview$n_dropout_flag[overview$participant == "P02"], 1)
})

test_that("session quality helpers validate inputs", {
  qc <- data.frame(
    participant = c("P01", "P02"),
    metric = c(1, 2),
    text_metric = c("a", "b"),
    quality_index = c(0.8, 0.9),
    flag = c(TRUE, FALSE)
  )

  expect_error(compute_gazepoint_quality_index("not data", metric_cols = "metric"), "data frame")
  expect_error(compute_gazepoint_quality_index(qc, metric_cols = "missing"), "not found")
  expect_error(compute_gazepoint_quality_index(qc, metric_cols = "text_metric"), "numeric")
  expect_error(compute_gazepoint_quality_index(qc, metric_cols = "metric", directions = "sideways"), "higher")
  expect_error(compute_gazepoint_quality_index(qc, metric_cols = "metric", weights = -1), "non-negative")
  expect_error(compute_gazepoint_quality_index(qc, metric_cols = "metric"), "already exist")

  expect_error(
    audit_gazepoint_session_comparability(qc, metric_cols = "metric", group_cols = "missing"),
    "not found"
  )
  expect_error(
    audit_gazepoint_session_comparability(qc, metric_cols = "metric", z_threshold = 0),
    "positive"
  )

  expect_error(summarize_gazepoint_qc_overview(qc, quality_index_col = "missing"), "not found")
  expect_error(summarize_gazepoint_qc_overview(qc, flag_cols = "metric"), "logical")
  expect_error(summarize_gazepoint_qc_overview(qc, metric_cols = "text_metric"), "numeric")
})
