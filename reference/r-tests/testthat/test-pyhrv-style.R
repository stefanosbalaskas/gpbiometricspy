
test_that("pyHRV-style time-domain helpers work", {
  nni <- 800 + 40 * sin(seq(0, 8 * pi, length.out = 300))

  td <- compute_gazepoint_pyhrv_time_domain(nni, segment_seconds = 60)
  expect_true(is.data.frame(td))
  expect_true("sdnn" %in% names(td))
  expect_true("rmssd" %in% names(td))
  expect_true(is.finite(td$sdnn[1]))

  expect_true(is.data.frame(compute_gazepoint_pyhrv_nn50(nni)))
  expect_true(is.data.frame(compute_gazepoint_pyhrv_nn20(nni)))
})

test_that("pyHRV-style interval and utility helpers work", {
  peaks <- seq(0, 10, by = 0.8)
  nni <- extract_gazepoint_pyhrv_nn_intervals(peaks)
  expect_gt(length(nni), 5)
  expect_equal(round(mean(nni)), 800)

  hr <- compute_gazepoint_pyhrv_heart_rate(nni)
  expect_true(all(is.finite(hr)))

  seg <- segment_gazepoint_pyhrv_nni(rep(800, 300), segment_seconds = 60)
  expect_true(is.data.frame(seg))

  chk <- check_gazepoint_pyhrv_interval(c(800, NA, 3000))
  expect_true(is.data.frame(chk))
  expect_true(any(!chk$valid))
})

test_that("pyHRV-style frequency-domain helpers work", {
  nni <- 800 + 40 * sin(seq(0, 12 * pi, length.out = 400))

  welch <- compute_gazepoint_pyhrv_welch_psd(nni)
  expect_true(is.list(welch))
  expect_true(is.data.frame(welch$psd))
  expect_true(is.data.frame(welch$measures))

  lomb <- compute_gazepoint_pyhrv_lomb_psd(nni, n_freq = 128)
  expect_true(is.list(lomb))
  expect_true(is.data.frame(lomb$measures))

  ar <- compute_gazepoint_pyhrv_ar_psd(nni)
  expect_true(is.list(ar))
  expect_true(is.data.frame(ar$measures))

  cmp <- compare_gazepoint_pyhrv_psd_methods(nni, methods = c("welch", "lomb"))
  expect_true(is.data.frame(cmp$measures))
})

test_that("pyHRV-style nonlinear helpers work", {
  nni <- 800 + 30 * sin(seq(0, 8 * pi, length.out = 300)) + rnorm(300, 0, 3)

  pc <- compute_gazepoint_pyhrv_poincare(nni)
  expect_true(is.data.frame(pc))
  expect_true("sd1" %in% names(pc))

  se <- compute_gazepoint_pyhrv_sample_entropy(nni)
  expect_true(is.na(se) || is.finite(se))

  dfa <- compute_gazepoint_pyhrv_dfa(nni)
  expect_true(is.data.frame(dfa))

  nl <- compute_gazepoint_pyhrv_nonlinear(nni)
  expect_true(is.data.frame(nl))
})

test_that("pyHRV-style all-in-one runner and export work", {
  nni <- 800 + 25 * sin(seq(0, 8 * pi, length.out = 300))

  out <- run_gazepoint_pyhrv_style(nni_ms = nni)
  expect_true(is.list(out))
  expect_true(is.data.frame(out$time_domain))
  expect_true(is.data.frame(out$nonlinear))

  f <- tempfile(fileext = ".rds")
  export_gazepoint_pyhrv_results(out, f)
  imported <- import_gazepoint_pyhrv_results(f)
  expect_true(is.list(imported))
})

