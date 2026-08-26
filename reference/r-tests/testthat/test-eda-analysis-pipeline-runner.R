test_that("run_gazepoint_eda_analysis_pipeline returns a six-phase run object", {
  dat <- data.frame(
    source_file = "user1_all_gaze.csv",
    MEDIA_ID = 1,
    CNT = seq_len(120),
    GSR_US = 1 + sin(seq(0, 4 * pi, length.out = 120)) * 0.1,
    GSR_US_PHASIC = sin(seq(0, 8 * pi, length.out = 120)) * 0.03,
    HR = 70 + sin(seq(0, 2 * pi, length.out = 120)) * 3,
    IBI = rep(0.8, 120),
    DIAL = rep(1, 120)
  )

  out <- run_gazepoint_eda_analysis_pipeline(
    data = dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = c("source_file", "MEDIA_ID"),
    signal_cols = c("GSR_US", "GSR_US_PHASIC", "HR", "IBI", "DIAL"),
    sampling_rate = 60,
    prepare_external_bridges = FALSE,
    prepare_model_data = FALSE,
    create_reports = FALSE,
    continue_on_error = TRUE
  )

  expect_s3_class(out, "gazepoint_eda_analysis_pipeline_run")
  expect_equal(out$overview$phase_count, 6)
  expect_equal(out$overview$input_rows, 120)
  expect_equal(out$overview$eda_col, "GSR_US")
  expect_equal(out$overview$time_col, "CNT")
  expect_named(
    out$phases,
    c(
      "phase_1_ingestion_qc",
      "phase_2_preprocessing_peaks",
      "phase_3_external_bridges",
      "phase_4_sync_model_formatting",
      "phase_5_model_templates",
      "phase_6_reporting"
    )
  )
  expect_true(is.data.frame(out$model_templates))
  expect_true(is.data.frame(out$interpretation_guardrails))
})

test_that("run_gazepoint_eda_analysis_pipeline can prepare external bridge phase outputs", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq_len(60),
    GSR_US = seq(1, 2, length.out = 60),
    HR = 70 + sin(seq(0, 2 * pi, length.out = 60))
  )

  out <- run_gazepoint_eda_analysis_pipeline(
    data = dat,
    eda_col = "GSR_US",
    time_col = "CNT",
    group_cols = "participant",
    signal_cols = c("GSR_US", "HR"),
    sampling_rate = 60,
    prepare_external_bridges = TRUE,
    bridge_methods = c("cvxeda", "ledalab", "pspm"),
    prepare_model_data = FALSE,
    create_reports = FALSE,
    continue_on_error = TRUE
  )

  expect_s3_class(out, "gazepoint_eda_analysis_pipeline_run")
  expect_true("cvxeda" %in% names(out$phases$phase_3_external_bridges))
  expect_true("ledalab" %in% names(out$phases$phase_3_external_bridges))
  expect_true("pspm" %in% names(out$phases$phase_3_external_bridges))

  expect_false(inherits(out$phases$phase_3_external_bridges$cvxeda, "gazepoint_eda_pipeline_error"))
  expect_false(inherits(out$phases$phase_3_external_bridges$ledalab, "gazepoint_eda_pipeline_error"))
  expect_false(inherits(out$phases$phase_3_external_bridges$pspm, "gazepoint_eda_pipeline_error"))
})

test_that("run_gazepoint_eda_analysis_pipeline records errors when continuing", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq_len(10),
    HR = 70 + seq_len(10)
  )

  expect_error(
    run_gazepoint_eda_analysis_pipeline(
      data = dat,
      eda_col = "missing_gsr",
      time_col = "CNT",
      group_cols = "participant",
      continue_on_error = TRUE
    ),
    "missing_gsr"
  )
})

test_that("run_gazepoint_eda_analysis_pipeline stops on step errors when requested", {
  dat <- data.frame(
    participant = "p1",
    CNT = seq_len(20),
    GSR_US = seq(1, 2, length.out = 20)
  )

  expect_error(
    run_gazepoint_eda_analysis_pipeline(
      data = dat,
      eda_col = "GSR_US",
      time_col = "CNT",
      group_cols = "missing_group",
      continue_on_error = FALSE
    ),
    "missing_group"
  )
})
