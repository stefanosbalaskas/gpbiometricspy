test_that("HeartPy-style input preparation works", {
  fs <- 100
  t <- seq(0, 20, by = 1 / fs)
  signal <- sin(2 * pi * 1.2 * t)^8 + 0.05 * sin(2 * pi * 8 * t)
  d <- data.frame(participant = "P01", trial = "T01", time_s = t, pulse = signal)

  prep <- prepare_gazepoint_heartpy_input(
    d, signal_col = "pulse", time_col = "time_s",
    group_cols = c("participant", "trial")
  )

  expect_true(is.data.frame(prep$signal_table))
  expect_equal(nrow(prep$signal_table), nrow(d))
  expect_true(is.finite(prep$sampling_rate_hz))
})

test_that("PPG peak detection and measures work", {
  fs <- 100
  t <- seq(0, 20, by = 1 / fs)
  signal <- sin(2 * pi * 1.2 * t)^8 + 0.02 * sin(2 * pi * 6 * t)
  d <- data.frame(time_s = t, pulse = signal)

  det <- detect_gazepoint_ppg_peaks(
    d, signal_col = "pulse", time_col = "time_s",
    sampling_rate_hz = fs,
    bpm_min = 40, bpm_max = 140,
    enhance_peaks = FALSE,
    lowpass_hz = NULL,
    hampel = FALSE,
    high_precision = FALSE
  )

  expect_true(is.list(det))
  expect_true(is.data.frame(det$peaks))
  expect_gt(nrow(det$peaks), 10)

  rejected <- reject_gazepoint_ppg_peaks(det$peaks)
  expect_true("accepted" %in% names(rejected))

  measures <- compute_gazepoint_ppg_measures(rejected)
  expect_true(is.data.frame(measures))
  expect_true("bpm" %in% names(measures))
  expect_true(is.finite(measures$bpm[1]) || is.na(measures$bpm[1]))
})

test_that("clipping, filtering, enhancement, and Hampel helpers return numeric vectors", {
  fs <- 100
  t <- seq(0, 5, by = 1 / fs)
  x <- sin(2 * pi * 1.2 * t)^8
  x[100:103] <- max(x)

  clip <- reconstruct_gazepoint_ppg_clipping(x)
  expect_equal(length(clip$signal), length(x))
  expect_equal(length(clip$clipped), length(x))

  enh <- enhance_gazepoint_ppg_peaks(x, fs, iterations = 1)
  expect_equal(length(enh), length(x))

  filt <- filter_gazepoint_ppg_butterworth(x, cutoff_hz = 5, sampling_rate_hz = fs)
  expect_equal(length(filt), length(x))

  ham <- correct_gazepoint_ppg_hampel(x, fs)
  expect_equal(length(ham), length(x))
})

test_that("breathing-rate and report helpers work", {
  rr <- 800 + 50 * sin(seq(0, 20, length.out = 40))
  br <- estimate_gazepoint_breathing_rate_from_ibi(rr)
  expect_true(is.list(br))
  expect_true("breathing_rate_hz" %in% names(br))

  fs <- 100
  t <- seq(0, 12, by = 1 / fs)
  signal <- sin(2 * pi * 1.1 * t)^8
  d <- data.frame(time_s = t, pulse = signal)
  det <- detect_gazepoint_ppg_peaks(d, "pulse", "time_s", sampling_rate_hz = fs, high_precision = FALSE)
  rep <- create_gazepoint_heartpy_report(det)
  expect_true(is.list(rep))
  expect_true(is.data.frame(rep$measures))
})
