
# Synthetic Gazepoint eye-tracking data generator

.gp_sim_param <- function(params, name, default) {
  if (!is.list(params)) {
    stop("`params` must be a named list.", call. = FALSE)
  }

  if (!is.null(params[[name]])) {
    params[[name]]
  } else {
    default
  }
}

.gp_sim_scalar <- function(x, name, min_value = NULL, max_value = NULL) {
  if (length(x) != 1L || !is.numeric(x) || !is.finite(x)) {
    stop("`params$", name, "` must be a single finite numeric value.", call. = FALSE)
  }

  if (!is.null(min_value) && x < min_value) {
    stop("`params$", name, "` must be >= ", min_value, ".", call. = FALSE)
  }

  if (!is.null(max_value) && x > max_value) {
    stop("`params$", name, "` must be <= ", max_value, ".", call. = FALSE)
  }

  x
}

.gp_sim_clip <- function(x, lower = 0, upper = 1) {
  pmin(pmax(x, lower), upper)
}

.gp_sim_make_fixations <- function(time_s,
                                   n_fixations = NULL,
                                   fixation_mean_s = 0.35,
                                   fixation_sd_s = 0.10,
                                   screen_bounds = c(0, 1, 0, 1),
                                   gaze_noise_sd = 0.015,
                                   saccade_samples = 3L) {
  n <- length(time_s)

  if (is.null(n_fixations)) {
    duration <- max(time_s, na.rm = TRUE) - min(time_s, na.rm = TRUE)
    n_fixations <- max(1L, round(duration / fixation_mean_s))
  }

  n_fixations <- max(1L, as.integer(n_fixations))
  saccade_samples <- max(1L, as.integer(saccade_samples))

  fixation_lengths <- pmax(
    saccade_samples + 2L,
    round(stats::rnorm(
      n_fixations,
      mean = fixation_mean_s / stats::median(diff(time_s), na.rm = TRUE),
      sd = fixation_sd_s / stats::median(diff(time_s), na.rm = TRUE)
    ))
  )

  while (sum(fixation_lengths) < n) {
    fixation_lengths <- c(fixation_lengths, sample(fixation_lengths, 1L))
  }

  fixation_lengths[length(fixation_lengths)] <- fixation_lengths[length(fixation_lengths)] -
    (sum(fixation_lengths) - n)

  fixation_lengths <- fixation_lengths[fixation_lengths > 0]
  n_fixations <- length(fixation_lengths)

  centers_x <- stats::runif(n_fixations, screen_bounds[1L] + 0.08, screen_bounds[2L] - 0.08)
  centers_y <- stats::runif(n_fixations, screen_bounds[3L] + 0.08, screen_bounds[4L] - 0.08)

  fixation_id <- rep(seq_len(n_fixations), fixation_lengths)
  fixation_id <- fixation_id[seq_len(n)]

  gaze_x <- numeric(n)
  gaze_y <- numeric(n)

  start <- 1L

  for (i in seq_len(n_fixations)) {
    idx <- start:(start + fixation_lengths[i] - 1L)

    gaze_x[idx] <- centers_x[i] + stats::rnorm(length(idx), 0, gaze_noise_sd)
    gaze_y[idx] <- centers_y[i] + stats::rnorm(length(idx), 0, gaze_noise_sd)

    if (i > 1L && length(idx) > saccade_samples) {
      trans_idx <- idx[seq_len(min(saccade_samples, length(idx)))]
      alpha <- seq(0, 1, length.out = length(trans_idx))
      gaze_x[trans_idx] <- (1 - alpha) * centers_x[i - 1L] + alpha * centers_x[i] +
        stats::rnorm(length(trans_idx), 0, gaze_noise_sd * 2)
      gaze_y[trans_idx] <- (1 - alpha) * centers_y[i - 1L] + alpha * centers_y[i] +
        stats::rnorm(length(trans_idx), 0, gaze_noise_sd * 2)
    }

    start <- start + fixation_lengths[i]
  }

  list(
    gaze_x = .gp_sim_clip(gaze_x, screen_bounds[1L], screen_bounds[2L]),
    gaze_y = .gp_sim_clip(gaze_y, screen_bounds[3L], screen_bounds[4L]),
    fixation_id = fixation_id
  )
}

.gp_sim_make_blinks <- function(n,
                                sampling_rate_hz = 60,
                                blink_rate_per_min = 15,
                                blink_duration_mean_s = 0.15,
                                blink_duration_sd_s = 0.04) {
  total_minutes <- n / sampling_rate_hz / 60
  expected_blinks <- blink_rate_per_min * total_minutes
  n_blinks <- stats::rpois(1L, lambda = expected_blinks)

  in_blink <- rep(FALSE, n)
  blink_id <- rep(NA_integer_, n)

  if (n_blinks <= 0L) {
    return(list(in_blink = in_blink, blink_id = blink_id))
  }

  blink_lengths <- pmax(
    1L,
    round(stats::rnorm(
      n_blinks,
      mean = blink_duration_mean_s * sampling_rate_hz,
      sd = blink_duration_sd_s * sampling_rate_hz
    ))
  )

  possible_starts <- seq_len(max(1L, n - max(blink_lengths) - 1L))

  if (!length(possible_starts)) {
    return(list(in_blink = in_blink, blink_id = blink_id))
  }

  starts <- sort(sample(possible_starts, size = min(n_blinks, length(possible_starts)), replace = FALSE))

  for (i in seq_along(starts)) {
    idx <- starts[i]:min(n, starts[i] + blink_lengths[i] - 1L)
    in_blink[idx] <- TRUE
    blink_id[idx] <- i
  }

  list(in_blink = in_blink, blink_id = blink_id)
}

#' Simulate Gazepoint-style gaze and pupil data
#'
#' Generates synthetic Gazepoint-like eye-tracking data with time stamps, gaze
#' coordinates, fixation identifiers, pupil diameter, validity columns, and
#' random blink intervals. The output is intended for teaching, examples,
#' testing, smoke tests, and vignette demonstrations; it is not a physiological
#' ground-truth simulator.
#'
#' @param params Named list of simulation parameters. Supported entries include
#'   `n`, `duration_s`, `sampling_rate_hz`, `seed`, `participant_id`, `trial_id`,
#'   `screen_bounds`, `n_fixations`, `fixation_mean_s`, `fixation_sd_s`,
#'   `gaze_noise_sd`, `saccade_samples`, `pupil_mean`, `pupil_sd`,
#'   `pupil_drift_sd`, `blink_rate_per_min`, `blink_duration_mean_s`,
#'   `blink_duration_sd_s`, `include_invalid_gaze`, and
#'   `invalid_gaze_prop`.
#'
#' @return A data frame with Gazepoint-style columns, including `time_s`,
#'   `MSTIMER`, `BPOGX`, `BPOGY`, `FPOGX`, `FPOGY`, `LPD`, `RPD`, `LPV`, `RPV`,
#'   `fixation_id`, `in_blink`, `blink_id`, `participant`, and `trial`.
#' @export
#'
#' @examples
#' dat <- simulate_gazepoint_eye_data(list(n = 120, seed = 1))
#' head(dat)
simulate_gazepoint_eye_data <- function(params = list()) {
  if (is.null(params)) {
    params <- list()
  }

  if (!is.list(params)) {
    stop("`params` must be a named list.", call. = FALSE)
  }

  seed <- .gp_sim_param(params, "seed", NULL)

  if (!is.null(seed)) {
    old_seed <- if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
      get(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    } else {
      NULL
    }

    on.exit({
      if (!is.null(old_seed)) {
        assign(".Random.seed", old_seed, envir = .GlobalEnv)
      }
    }, add = TRUE)

    set.seed(seed)
  }

  sampling_rate_hz <- .gp_sim_scalar(
    .gp_sim_param(params, "sampling_rate_hz", 60),
    "sampling_rate_hz",
    min_value = 1
  )

  n <- .gp_sim_param(params, "n", NULL)
  duration_s <- .gp_sim_param(params, "duration_s", NULL)

  if (is.null(n)) {
    if (is.null(duration_s)) {
      n <- 600L
    } else {
      duration_s <- .gp_sim_scalar(duration_s, "duration_s", min_value = 0.001)
      n <- max(1L, as.integer(round(duration_s * sampling_rate_hz)))
    }
  }

  n <- as.integer(.gp_sim_scalar(n, "n", min_value = 1))

  participant_id <- as.character(.gp_sim_param(params, "participant_id", "P01"))
  trial_id <- as.character(.gp_sim_param(params, "trial_id", "T01"))

  screen_bounds <- .gp_sim_param(params, "screen_bounds", c(0, 1, 0, 1))

  if (length(screen_bounds) != 4L || any(!is.finite(screen_bounds))) {
    stop("`params$screen_bounds` must be c(x_min, x_max, y_min, y_max).", call. = FALSE)
  }

  time_s <- seq(0, by = 1 / sampling_rate_hz, length.out = n)
  mstimer <- round(time_s * 1000)

  fixation_mean_s <- .gp_sim_scalar(
    .gp_sim_param(params, "fixation_mean_s", 0.35),
    "fixation_mean_s",
    min_value = 0.01
  )

  fixation_sd_s <- .gp_sim_scalar(
    .gp_sim_param(params, "fixation_sd_s", 0.10),
    "fixation_sd_s",
    min_value = 0
  )

  gaze_noise_sd <- .gp_sim_scalar(
    .gp_sim_param(params, "gaze_noise_sd", 0.015),
    "gaze_noise_sd",
    min_value = 0
  )

  saccade_samples <- as.integer(.gp_sim_scalar(
    .gp_sim_param(params, "saccade_samples", 3),
    "saccade_samples",
    min_value = 1
  ))

  fixation <- .gp_sim_make_fixations(
    time_s = time_s,
    n_fixations = .gp_sim_param(params, "n_fixations", NULL),
    fixation_mean_s = fixation_mean_s,
    fixation_sd_s = fixation_sd_s,
    screen_bounds = screen_bounds,
    gaze_noise_sd = gaze_noise_sd,
    saccade_samples = saccade_samples
  )

  blink_rate_per_min <- .gp_sim_scalar(
    .gp_sim_param(params, "blink_rate_per_min", 15),
    "blink_rate_per_min",
    min_value = 0
  )

  blink_duration_mean_s <- .gp_sim_scalar(
    .gp_sim_param(params, "blink_duration_mean_s", 0.15),
    "blink_duration_mean_s",
    min_value = 0.001
  )

  blink_duration_sd_s <- .gp_sim_scalar(
    .gp_sim_param(params, "blink_duration_sd_s", 0.04),
    "blink_duration_sd_s",
    min_value = 0
  )

  blinks <- .gp_sim_make_blinks(
    n = n,
    sampling_rate_hz = sampling_rate_hz,
    blink_rate_per_min = blink_rate_per_min,
    blink_duration_mean_s = blink_duration_mean_s,
    blink_duration_sd_s = blink_duration_sd_s
  )

  pupil_mean <- .gp_sim_scalar(.gp_sim_param(params, "pupil_mean", 3.2), "pupil_mean", min_value = 0)
  pupil_sd <- .gp_sim_scalar(.gp_sim_param(params, "pupil_sd", 0.08), "pupil_sd", min_value = 0)
  pupil_drift_sd <- .gp_sim_scalar(.gp_sim_param(params, "pupil_drift_sd", 0.003), "pupil_drift_sd", min_value = 0)

  drift <- cumsum(stats::rnorm(n, 0, pupil_drift_sd))
  pupil_base <- pupil_mean + drift + stats::rnorm(n, 0, pupil_sd)

  lpd <- pupil_base + stats::rnorm(n, 0, pupil_sd / 3)
  rpd <- pupil_base + stats::rnorm(n, 0, pupil_sd / 3)

  lpv <- rep(1L, n)
  rpv <- rep(1L, n)

  lpd[blinks$in_blink] <- NA_real_
  rpd[blinks$in_blink] <- NA_real_
  lpv[blinks$in_blink] <- 0L
  rpv[blinks$in_blink] <- 0L

  bpogx <- fixation$gaze_x
  bpogy <- fixation$gaze_y

  include_invalid_gaze <- isTRUE(.gp_sim_param(params, "include_invalid_gaze", FALSE))
  invalid_gaze_prop <- .gp_sim_scalar(
    .gp_sim_param(params, "invalid_gaze_prop", 0.02),
    "invalid_gaze_prop",
    min_value = 0,
    max_value = 1
  )

  gaze_valid <- rep(TRUE, n)

  if (include_invalid_gaze && invalid_gaze_prop > 0) {
    n_bad <- max(1L, round(n * invalid_gaze_prop))
    bad_idx <- sample(seq_len(n), size = min(n_bad, n), replace = FALSE)

    bpogx[bad_idx] <- stats::runif(length(bad_idx), screen_bounds[2L] + 0.05, screen_bounds[2L] + 0.50)
    bpogy[bad_idx] <- stats::runif(length(bad_idx), screen_bounds[3L], screen_bounds[4L])
    gaze_valid[bad_idx] <- FALSE
  }

  out <- data.frame(
    participant = participant_id,
    trial = trial_id,
    sample_id = seq_len(n),
    time_s = time_s,
    MSTIMER = mstimer,
    BPOGX = bpogx,
    BPOGY = bpogy,
    FPOGX = bpogx,
    FPOGY = bpogy,
    LPD = lpd,
    RPD = rpd,
    LPV = lpv,
    RPV = rpv,
    fixation_id = fixation$fixation_id,
    in_blink = blinks$in_blink,
    blink_id = blinks$blink_id,
    gaze_valid_simulated = gaze_valid,
    stringsAsFactors = FALSE
  )

  attr(out, "simulation_params") <- params
  attr(out, "sampling_rate_hz") <- sampling_rate_hz
  attr(out, "screen_bounds") <- screen_bounds

  out
}

