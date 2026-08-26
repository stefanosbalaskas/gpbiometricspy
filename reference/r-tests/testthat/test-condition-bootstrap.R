
test_that("compare_gazepoint_conditions_bootstrap compares independent rows", {
  set.seed(1)

  dat <- data.frame(
    condition = rep(c("control", "treatment"), each = 40),
    outcome = c(rnorm(40, mean = 0), rnorm(40, mean = 1))
  )

  out <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    condition_levels = c("control", "treatment"),
    n_boot = 300,
    seed = 10
  )

  expect_true(inherits(out, "gazepoint_bootstrap_condition_comparison"))
  expect_equal(nrow(out), 1)
  expect_true(out$estimate > 0.5)
  expect_true(out$ci_high > out$ci_low)
  expect_equal(out$contrast, "treatment - control")
})

test_that("compare_gazepoint_conditions_bootstrap supports paired participant bootstrap", {
  set.seed(2)

  participant <- paste0("P", sprintf("%02d", 1:30))

  dat <- data.frame(
    participant = rep(participant, each = 2),
    condition = rep(c("pre", "post"), times = 30)
  )

  base <- rnorm(30)
  dat$outcome <- as.vector(rbind(base, base + 0.5 + rnorm(30, sd = 0.05)))

  out <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    participant_col = "participant",
    condition_levels = c("pre", "post"),
    paired = TRUE,
    n_boot = 300,
    seed = 20
  )

  expect_equal(out$n_pairs, 30)
  expect_true(out$estimate > 0.4)
  expect_true(out$unit_level == "participant_condition_mean")
})

test_that("compare_gazepoint_conditions_bootstrap averages participant trial data", {
  set.seed(3)

  dat <- data.frame(
    participant = rep(paste0("P", 1:20), each = 10),
    condition = rep(rep(c("A", "B"), each = 5), times = 20)
  )

  dat$outcome <- ifelse(dat$condition == "B", 1, 0) + rnorm(nrow(dat), sd = 0.2)

  out <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    participant_col = "participant",
    condition_levels = c("A", "B"),
    n_boot = 300,
    seed = 30
  )

  expect_equal(out$n_condition_1, 20)
  expect_equal(out$n_condition_2, 20)
  expect_true(out$estimate > 0.8)
})

test_that("compare_gazepoint_conditions_bootstrap supports by_cols", {
  set.seed(4)

  dat <- rbind(
    data.frame(group = "easy", condition = rep(c("A", "B"), each = 30),
               outcome = c(rnorm(30, 0), rnorm(30, 0.5))),
    data.frame(group = "hard", condition = rep(c("A", "B"), each = 30),
               outcome = c(rnorm(30, 0), rnorm(30, 1.5)))
  )

  out <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    condition_levels = c("A", "B"),
    by_cols = "group",
    n_boot = 300,
    seed = 40
  )

  expect_equal(nrow(out), 2)
  expect_true(all(c("easy", "hard") %in% out$group))
  expect_true(out$estimate[out$group == "hard"] > out$estimate[out$group == "easy"])
})

test_that("compare_gazepoint_conditions_bootstrap supports standardized effects", {
  set.seed(5)

  dat <- data.frame(
    condition = rep(c("A", "B"), each = 50),
    outcome = c(rnorm(50, 0, 1), rnorm(50, 1, 1))
  )

  out <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    condition_levels = c("A", "B"),
    statistic = "standardized_mean_difference",
    n_boot = 300,
    seed = 50
  )

  expect_true(is.finite(out$estimate))
  expect_true(out$estimate > 0.5)
})

test_that("compare_gazepoint_conditions_bootstrap is reproducible with a fixed seed", {
  set.seed(123)

  dat <- data.frame(
    condition = rep(c("A", "B"), each = 20),
    outcome = c(rnorm(20), rnorm(20, 1))
  )

  out1 <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    condition_levels = c("A", "B"),
    n_boot = 100,
    seed = 99
  )

  out2 <- compare_gazepoint_conditions_bootstrap(
    dat,
    outcome_col = "outcome",
    condition_col = "condition",
    condition_levels = c("A", "B"),
    n_boot = 100,
    seed = 99
  )

  expect_equal(out1$estimate, out2$estimate)
  expect_equal(out1$ci_low, out2$ci_low)
  expect_equal(out1$ci_high, out2$ci_high)
  expect_equal(
    attr(out1, "bootstrap_samples")[[1]],
    attr(out2, "bootstrap_samples")[[1]]
  )
})
