test_that("audit_gazepoint_beats flags beat-time interval problems", {
  beats <- data.frame(
    participant = rep(c("P01", "P02"), each = 8),
    beat_time_ms = c(
      0, 800, 1600, 1850, 2700, 5200, 6000, 6800,
      0, 780, 1560, 2340, 3120, 3900, 3900, 4680
    )
  )

  audit <- audit_gazepoint_beats(
    beats,
    beat_time_col = "beat_time_ms",
    group_cols = "participant",
    min_ibi = 300,
    max_ibi = 2000,
    duplicate_tolerance = 0,
    max_relative_change = 1.0
  )

  expect_s3_class(audit, "gazepoint_beat_audit")
  expect_named(audit, c("beats", "summary", "parameters"))

  expect_true(all(c(
    "participant", "beat_index", "original_row", "beat_time", "ibi",
    "has_interval", "short_ibi", "long_ibi", "duplicate_time",
    "abrupt_change", "any_flag", "flag_reason"
  ) %in% names(audit$beats)))

  expect_equal(nrow(audit$beats), 16)
  expect_equal(nrow(audit$summary), 2)

  expect_true(any(audit$beats$short_ibi))
  expect_true(any(audit$beats$long_ibi))
  expect_true(any(audit$beats$duplicate_time))
  expect_true(any(audit$beats$abrupt_change))

  p01 <- audit$summary[audit$summary$participant == "P01", ]
  p02 <- audit$summary[audit$summary$participant == "P02", ]

  expect_equal(p01$n_flagged_beats, 3)
  expect_equal(p01$n_short_ibi, 1)
  expect_equal(p01$n_long_ibi, 1)
  expect_equal(p01$n_abrupt_change, 2)

  expect_equal(p02$n_flagged_beats, 1)
  expect_equal(p02$n_short_ibi, 1)
  expect_equal(p02$n_duplicate_time, 1)
})

test_that("audit_gazepoint_beats audits explicit IBI columns", {
  ibi_data <- data.frame(
    participant = "P03",
    ibi_ms = c(NA, 800, 790, 250, 810, 2600, 805)
  )

  audit <- audit_gazepoint_beats(
    ibi_data,
    ibi_col = "ibi_ms",
    group_cols = "participant",
    min_ibi = 300,
    max_ibi = 2000
  )

  expect_s3_class(audit, "gazepoint_beat_audit")
  expect_equal(nrow(audit$beats), 7)
  expect_equal(audit$summary$n_intervals, 7)
  expect_equal(audit$summary$n_nonfinite_ibi, 1)
  expect_equal(audit$summary$n_short_ibi, 1)
  expect_equal(audit$summary$n_long_ibi, 1)
  expect_equal(audit$summary$n_flagged_beats, 3)

  expect_true(audit$beats$nonfinite_ibi[1])
  expect_true(audit$beats$short_ibi[4])
  expect_true(audit$beats$long_ibi[6])
})

test_that("correct_gazepoint_beats masks flagged intervals by default", {
  beats <- data.frame(
    participant = rep(c("P01", "P02"), each = 8),
    beat_time_ms = c(
      0, 800, 1600, 1850, 2700, 5200, 6000, 6800,
      0, 780, 1560, 2340, 3120, 3900, 3900, 4680
    )
  )

  audit <- audit_gazepoint_beats(
    beats,
    beat_time_col = "beat_time_ms",
    group_cols = "participant",
    min_ibi = 300,
    max_ibi = 2000,
    duplicate_tolerance = 0,
    max_relative_change = 1.0
  )

  corrected <- correct_gazepoint_beats(audit, action = "mask")

  expect_s3_class(corrected, "gazepoint_beat_correction")
  expect_named(corrected, c("data", "correction_log", "summary", "parameters"))

  expect_true("ibi_corrected" %in% names(corrected$data))
  expect_equal(nrow(corrected$correction_log), 4)
  expect_equal(unique(corrected$correction_log$action), "mask")
  expect_true(all(is.na(corrected$correction_log$corrected_ibi)))

  flagged_rows <- corrected$data$any_flag
  expect_true(all(is.na(corrected$data$ibi_corrected[flagged_rows])))
  expect_equal(corrected$summary$n_corrections, c(3, 1))
  expect_equal(corrected$summary$n_masked, c(3, 1))
})

test_that("correct_gazepoint_beats can replace flagged intervals with local medians", {
  beats <- data.frame(
    participant = rep(c("P01", "P02"), each = 8),
    beat_time_ms = c(
      0, 800, 1600, 1850, 2700, 5200, 6000, 6800,
      0, 780, 1560, 2340, 3120, 3900, 3900, 4680
    )
  )

  audit <- audit_gazepoint_beats(
    beats,
    beat_time_col = "beat_time_ms",
    group_cols = "participant",
    min_ibi = 300,
    max_ibi = 2000,
    duplicate_tolerance = 0,
    max_relative_change = 1.0
  )

  corrected <- correct_gazepoint_beats(
    audit,
    action = "local_median",
    local_window = 2
  )

  expect_s3_class(corrected, "gazepoint_beat_correction")
  expect_equal(nrow(corrected$correction_log), 4)
  expect_equal(unique(corrected$correction_log$action), "local_median")
  expect_true(all(corrected$correction_log$correction_note == "replaced_with_local_median"))

  p01_log <- corrected$correction_log[corrected$correction_log$participant == "P01", ]
  p02_log <- corrected$correction_log[corrected$correction_log$participant == "P02", ]

  expect_equal(p01_log$corrected_ibi, c(800, 800, 800))
  expect_equal(p02_log$corrected_ibi, 780)

  expect_equal(corrected$summary$n_local_median, c(3, 1))
  expect_equal(corrected$summary$n_masked, c(0, 0))
})

test_that("summarize_gazepoint_beat_corrections aggregates correction logs", {
  log <- data.frame(
    participant = c("P01", "P01", "P02"),
    action = c("mask", "local_median", "local_median"),
    correction_note = c(
      "masked_flagged_interval",
      "replaced_with_local_median",
      "replaced_with_group_median"
    ),
    flag_reason = c("short_ibi", "long_ibi", "short_ibi"),
    original_ibi = c(250, 2500, 0),
    corrected_ibi = c(NA, 800, 780)
  )

  out <- summarize_gazepoint_beat_corrections(log, by = "participant")

  expect_equal(sort(out$participant), c("P01", "P02"))
  expect_equal(out$n_corrections[out$participant == "P01"], 2)
  expect_equal(out$n_masked[out$participant == "P01"], 1)
  expect_equal(out$n_local_median[out$participant == "P01"], 1)
  expect_equal(out$n_group_median[out$participant == "P02"], 1)
})

test_that("beat correction handles no-flag cases", {
  beats <- data.frame(
    participant = "P01",
    beat_time_ms = c(0, 800, 1600, 2400, 3200)
  )

  audit <- audit_gazepoint_beats(
    beats,
    beat_time_col = "beat_time_ms",
    group_cols = "participant",
    min_ibi = 300,
    max_ibi = 2000
  )

  corrected <- correct_gazepoint_beats(audit, action = "mask")

  expect_equal(sum(audit$beats$any_flag), 0)
  expect_equal(nrow(corrected$correction_log), 0)
  expect_equal(nrow(corrected$summary), 0)
  expect_true("ibi_corrected" %in% names(corrected$data))
})

test_that("beat audit and correction validate inputs", {
  demo <- data.frame(
    beat_time_ms = c(0, 800, 1600),
    ibi_ms = c(NA, 800, 800),
    label = c("a", "b", "c")
  )

  expect_error(
    audit_gazepoint_beats(demo),
    "Provide"
  )

  expect_error(
    audit_gazepoint_beats(demo, ibi_col = "missing"),
    "not found"
  )

  expect_error(
    audit_gazepoint_beats(demo, ibi_col = "label"),
    "numeric"
  )

  expect_error(
    audit_gazepoint_beats(
      demo,
      beat_time_col = "beat_time_ms",
      min_ibi = 2000,
      max_ibi = 300
    ),
    "smaller"
  )

  audit <- audit_gazepoint_beats(
    demo,
    ibi_col = "ibi_ms",
    min_ibi = 300,
    max_ibi = 2000
  )

  expect_error(
    correct_gazepoint_beats(
      audit,
      corrected_col = "ibi",
      overwrite = FALSE
    ),
    "already exists"
  )

  expect_error(
    correct_gazepoint_beats(audit, local_window = 0),
    "positive integer"
  )

  expect_error(
    summarize_gazepoint_beat_corrections(data.frame(x = 1)),
    "missing required"
  )
})
