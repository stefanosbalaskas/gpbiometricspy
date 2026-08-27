args <- commandArgs(trailingOnly = TRUE)
out_path <- if (length(args)) args[[1]] else "artifacts/golden/r.json"

if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is required")

# Source the frozen implementation in several passes. Some compatibility-alias
# files contain top-level assignments to functions defined in other files.
files <- sort(list.files("reference/R", pattern = "\\.R$", full.names = TRUE))
remaining <- files
for (pass in seq_len(4L)) {
  next_remaining <- character()
  for (f in remaining) {
    ok <- tryCatch({ sys.source(f, envir = .GlobalEnv); TRUE }, error = function(e) FALSE)
    if (!ok) next_remaining <- c(next_remaining, f)
  }
  if (!length(next_remaining)) break
  remaining <- next_remaining
}
if (length(remaining)) message("Some unrelated frozen R files could not be sourced in this minimal golden-fixture environment: ", paste(basename(remaining), collapse=", "))
required_functions <- c(
  "convert_gazepoint_gsr_to_conductance", "normalize_gazepoint_scr",
  "compute_gazepoint_pyhrv_sdnn", "compute_gazepoint_pyhrv_rmssd", "compute_gazepoint_pyhrv_sdsd",
  "compute_gazepoint_pyhrv_nn20", "compute_gazepoint_pyhrv_nn50", "smooth_gazepoint_pupil",
  "extract_gazepoint_ttl_events", "standardize_gazepoint_zscore",
  "baseline_correct_gazepoint_gsr", "baseline_correct_gazepoint_hr"
)
missing_required <- required_functions[!vapply(required_functions, exists, logical(1), mode="function", inherits=TRUE)]
if (length(missing_required)) stop("Required frozen R functions were not sourced: ", paste(missing_required, collapse=", "))

clean <- function(x) {
  if (is.data.frame(x)) return(lapply(x, function(col) as.list(clean(col))))
  if (is.list(x)) return(lapply(x, clean))
  if (is.numeric(x)) { x <- as.numeric(x); x[!is.finite(x)] <- NA_real_; return(x) }
  if (is.integer(x)) return(as.integer(x))
  if (is.logical(x)) return(x)
  as.character(x)
}

out <- list()
ohms <- data.frame(GSR_OHMS=c(1000000,500000,250000,NA_real_))
out$gsr_ohms_to_us <- convert_gazepoint_gsr_to_conductance(ohms,input_unit="ohms")$GSR_US
kohms <- data.frame(GSR_KOHMS=c(1000,500,250,NA_real_))
out$gsr_kohms_to_us <- convert_gazepoint_gsr_to_conductance(kohms,gsr_col="GSR_KOHMS",input_unit="kohms")$GSR_US
scr <- c(.1,.2,.4,NA_real_)
for (method in c("percent_max","range","center","z","log_z")) out[[paste0("scr_",method)]] <- normalize_gazepoint_scr(scr,method=method)
nni <- c(800,810,790,805,795,815)
out$pyhrv_sdnn <- compute_gazepoint_pyhrv_sdnn(nni)
out$pyhrv_rmssd <- compute_gazepoint_pyhrv_rmssd(nni)
out$pyhrv_sdsd <- compute_gazepoint_pyhrv_sdsd(nni)
out$pyhrv_nn20 <- compute_gazepoint_pyhrv_nn20(nni)
out$pyhrv_nn50 <- compute_gazepoint_pyhrv_nn50(nni)
pup <- data.frame(participant=rep("P01",6),pupil_left=c(3,3.2,3.4,NA,3.3,3.1))
out$pupil_moving_average <- smooth_gazepoint_pupil(pup,pupil_cols="pupil_left",id_cols="participant",window=3)$data$pupil_left_smooth
ttl <- data.frame(CNT=0:5,TTLV=rep(1,6),TTL0=c(0,1,1,0,2,2))
ev <- extract_gazepoint_ttl_events(ttl,ttl_columns="TTL0")
out$ttl_changes <- list(ttl_value=ev$ttl_value,previous_ttl_value=ev$previous_ttl_value,event_order=ev$event_order)
z <- data.frame(participant=c(rep("A",3),rep("B",3)),SCR_Amplitude=c(1,2,3,10,12,14))
out$zscore_grouped <- standardize_gazepoint_zscore(z,signal_col="SCR_Amplitude",group_col="participant")$SCR_Amplitude_Z
bg <- data.frame(participant=rep("A",4),GSR_US=c(1,2,3,4),GSRV=rep(1,4))
out$baseline_gsr <- baseline_correct_gazepoint_gsr(bg,baseline_rows=c(TRUE,TRUE,FALSE,FALSE),group_columns="participant")$GSR_US_baseline_corrected
bh <- data.frame(participant=rep("A",4),HR=c(60,62,65,67),HRV=rep(1,4))
out$baseline_hr <- baseline_correct_gazepoint_hr(bh,baseline_rows=c(TRUE,TRUE,FALSE,FALSE),group_columns="participant")$HR_baseline_corrected

dir.create(dirname(out_path), recursive=TRUE, showWarnings=FALSE)
jsonlite::write_json(lapply(out,clean), out_path, auto_unbox=TRUE, pretty=TRUE, null="null", na="null")
cat("wrote", out_path, "\n")
