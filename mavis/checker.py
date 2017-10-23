"""
module responsible for checking MAVIS output. Determines if jobs completed correctly and
what the status of the pipeline is
"""
import glob
import os
import re

from .constants import COMPLETE_STAMP, DISEASE_STATUS, SUBCOMMAND, PROTOCOL
from .util import bash_expands, log, MavisNamespace, unique_exists


LIBRARY_DIR_REGEX = r'^[\w-]+_({})_({})$'.format('|'.join(DISEASE_STATUS.values()), '|'.join(PROTOCOL.values()))
SGE_LOG_PATTERN = r'*.o*'
LOG_PATTERN = r'*.log'
BATCH_ID_PATTERN = 'batch-[0-9a-zA-Z-]+'

LOGFILE_STATUS = MavisNamespace(
    EMPTY='empty',
    CRASH='crash',
    INCOMPLETE='incomplete',
    COMPLETE='complete'
)


class LogDetails:
    """
    stores information about the log status
    """
    def __init__(self, filename):
        self.filename = filename
        self.status = None
        self.message = None
        self.run_time = None
        self.last_mod = None

        with open(filename, 'r') as fh:
            lines = fh.readlines()
            if not lines:
                self.status = LOGFILE_STATUS.EMPTY
            elif 'error' in lines[-1].lower():
                self.status = LOGFILE_STATUS.CRASH
                self.message = lines[-1].strip()
            else:
                run_time = None
                for line in lines[-10:]:
                    match = re.match(r'^\s*run time \(s\): (\d+)\s*$', line)
                    if match:
                        run_time = int(match.group(1))
                        break
                if run_time is None:
                    self.status = LOGFILE_STATUS.INCOMPLETE
                    self.message = lines[-1].strip()
                    self.last_mod = os.path.getmtime(filename)
                else:
                    self.run_time = run_time
                    self.status = LOGFILE_STATUS.COMPLETE


class PipelineStageRun:

    def __init__(self, name, output_dir):
        self.name = name
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            raise OSError('missing output_dir', output_dir)
        self.times = {}
        self.logs = {}
        self.stamps = {}
        self.job_ids = set()
        self.single = True
        self.max_run_time = None
        self.total_run_time = None
        self.avg_run_time = None

        if self.name in [SUBCOMMAND.ANNOTATE, SUBCOMMAND.VALIDATE, SUBCOMMAND.CLUSTER]:
            self.single = False
            for dirname in glob.glob(os.path.join(output_dir, '*')):
                name = os.path.basename(dirname)
                match = re.match(r'^' + BATCH_ID_PATTERN + r'-(\d+)(\.tab)?$', name)
                if match:
                    self.job_ids.add(int(match.group(1)))
            if not self.job_ids:
                self.job_ids.add(1)

    def report(self, indent='  ', indent_level=0, time_stamp=False):
        """
        parses log files and checks for complete stamps. Reports any errors observed

        Returns:
            bool: success
                - True: no errors or incomplete files were found
                - False: some errors or incomplete files
        """
        for job_task_id in self.job_ids:
            self.collect_log(job_task_id)
            self.collect_stamp(job_task_id)

        if self.single:
            self.collect_log()
            self.collect_stamp()
            self.job_ids = {None}

        incomplete_jobs = set()
        missing_logs = set()
        missing_stamp = set()
        missing_both = set()
        errors = set()

        for job_task_id in sorted(self.job_ids):
            if job_task_id in self.stamps:
                if job_task_id not in self.logs:
                    # complete but unlogged?
                    missing_logs.add(job_task_id)
            else:
                if job_task_id in self.logs:
                    logfile = self.logs[job_task_id]
                    if logfile.status == LOGFILE_STATUS.CRASH:
                        errors.add(job_task_id)
                    elif logfile.status == LOGFILE_STATUS.COMPLETE:
                        missing_stamp.add(job_task_id)
                    else:
                        incomplete_jobs.add(job_task_id)
                else:
                    missing_both.add(job_task_id)

        # report the overall status
        if not any([self.job_ids, self.logs, self.stamps]):
            log(indent * indent_level + self.name, 'FAIL', time_stamp=time_stamp)
            log(indent * indent_level + '  no files found: stage not started, or skipped', time_stamp=False)
            return False
        elif any([incomplete_jobs, missing_both, missing_logs, missing_stamp, errors]):
            log(indent * indent_level + self.name, 'FAIL', time_stamp=time_stamp)
            # summarize the errors
            if None not in self.job_ids or len(self.job_ids) > 1:
                if missing_logs:
                    log('{}{} jobs stamped complete but missing log files (jobs: {})'.format(
                        indent * (indent_level + 1), len(missing_logs), convert_set_to_ranges(missing_logs)), time_stamp=False)
                if missing_stamp:
                    log('{}{} jobs logged complete but missing stamp (jobs: {})'.format(
                        indent * (indent_level + 1), len(missing_stamp), convert_set_to_ranges(missing_stamp)), time_stamp=False)
                if missing_both:
                    log('{}{} jobs not started (no log/stamp) (jobs: {})'.format(
                        indent * (indent_level + 1), len(missing_both), convert_set_to_ranges(missing_both)), time_stamp=False)
                if incomplete_jobs:
                    log('{}{} jobs running, incomplete without errors (jobs: {})'.format(
                        indent * (indent_level + 1), len(incomplete_jobs), convert_set_to_ranges(incomplete_jobs)), time_stamp=False)
                if errors:
                    log('{}{} jobs CRASHED (jobs: {})'.format(
                        indent * (indent_level + 1), len(errors), convert_set_to_ranges(errors)), time_stamp=False)
                    details = {}
                    for job_task_id in errors:
                        logfile = self.logs[job_task_id]
                        details.setdefault(logfile.message, set()).add(job_task_id)
                    for msg, jobs in details.items():
                        log('{}{} (jobs: {})'.format(indent * (indent_level + 2), msg, convert_set_to_ranges(jobs)), time_stamp=False)
            else:
                if missing_logs:
                    log(indent * (indent_level + 1) + 'job stamped complete but missing log file', time_stamp=False)
                if missing_stamp:
                    log(indent * (indent_level + 1) + 'job logged complete but missing complete stamp', time_stamp=False)
                if missing_both:
                    log(indent * (indent_level + 1) + 'job not started (no log/stamp)', time_stamp=False)
                if incomplete_jobs:
                    log(indent * (indent_level + 1) + 'job running, incomplete without errors', time_stamp=False)
                if errors:
                    log(indent * (indent_level + 1) + 'job CRASHED', self.logs[None].message, time_stamp=False)
            return False if any([incomplete_jobs, missing_both, missing_stamp, errors]) else True
        else:
            log(indent * indent_level + self.name, 'OK', time_stamp=time_stamp)
            run_times = [j.run_time for j in self.logs.values() if j.run_time is not None]
            if run_times:
                self.max_run_time = max(run_times)
                self.total_run_time = sum(run_times)
                self.avg_run_time = int(round(self.total_run_time / len(run_times), 0))
                if self.name in [SUBCOMMAND.ANNOTATE, SUBCOMMAND.VALIDATE]:
                    log(indent * (indent_level + 1) + 'run time (s): {} (max), {} (total), {} (average)'.format(
                        self.max_run_time, self.total_run_time, self.avg_run_time), time_stamp=False)
                else:
                    log(indent * (indent_level + 1) + 'run time (s):', self.max_run_time, time_stamp=False)
            else:
                log(indent * (indent_level + 1) + 'error parsing run-times from the log files', time_stamp=False)
            return True

    def collect_stamp(self, job_task_id=None):
        """
        finds and stores the job complete stamp
        """
        if self.name in [SUBCOMMAND.ANNOTATE, SUBCOMMAND.VALIDATE]:
            # annotation and validation are setup in subdirectories each with their own complete stamp
            stamp_pattern = os.path.join(self.output_dir, '*-' + str(job_task_id), COMPLETE_STAMP)
        elif self.name == SUBCOMMAND.CLUSTER:
            stamp_pattern = os.path.join(self.output_dir, COMPLETE_STAMP)  # single stamp for top-level directory
        elif self.name in [SUBCOMMAND.SUMMARY, SUBCOMMAND.PAIR]:
            stamp_pattern = os.path.join(self.output_dir, COMPLETE_STAMP)  # single stamp for top-level directory
        else:
            raise NotImplementedError('checker has not been implemented for pipeline stage', self.name)

        # collect the log and complete stamp files
        try:
            self.stamps[job_task_id] = unique_exists(stamp_pattern)
        except OSError:
            pass

    def collect_log(self, job_task_id=None):
        """
        finds and stores the job log file
        """
        if self.name in [SUBCOMMAND.ANNOTATE, SUBCOMMAND.VALIDATE]:
            # annotation and validation are setup in subdirectories each with their own complete stamp
            patterns = [
                os.path.join(self.output_dir, '{}.{}'.format(SGE_LOG_PATTERN, job_task_id)),  # old log pattern
                os.path.join(self.output_dir, '*-{}'.format(job_task_id), LOG_PATTERN),  # single job
                os.path.join(self.output_dir, LOG_PATTERN)  # old log pattern manual run
            ]
            for log_pattern in patterns:
                try:
                    self.logs[job_task_id] = LogDetails(unique_exists(log_pattern, allow_none=False, get_newest=True))
                except OSError:
                    pass
                else:
                    break
        else:
            patterns = [
                os.path.join(self.output_dir, SGE_LOG_PATTERN),  # single job
                os.path.join(self.output_dir, LOG_PATTERN)  # manual run
            ]
            for log_pattern in patterns:
                try:
                    self.logs[job_task_id] = LogDetails(unique_exists(log_pattern, allow_none=False, get_newest=True))
                except OSError:
                    pass
                else:
                    break


class LibraryRun:
    """
    stores run information for pipeline steps that are run on individual libraries
    """
    def __init__(self, name, output_dir):
        self.name = name
        self.output_dir = output_dir
        self.max_run_time = 0
        self.total_run_time = 0
        self.avg_run_time = 0
        self.log_parse_error = False
        try:
            self.cluster = PipelineStageRun(SUBCOMMAND.CLUSTER, os.path.join(output_dir, SUBCOMMAND.CLUSTER))
        except OSError:
            self.cluster = None
        try:
            self.validation = PipelineStageRun(SUBCOMMAND.VALIDATE, os.path.join(output_dir, SUBCOMMAND.VALIDATE))
        except OSError:
            self.validation = None
        try:
            self.annotation = PipelineStageRun(SUBCOMMAND.ANNOTATE, os.path.join(output_dir, SUBCOMMAND.ANNOTATE))
        except OSError:
            self.annotation = None

    def report(self):
        result = True
        collective_job_ids = self.cluster.job_ids | self.annotation.job_ids
        if self.validation:
            collective_job_ids.update(self.validation.job_ids)
            self.validation.job_ids.update(collective_job_ids)
        self.cluster.job_ids.update(collective_job_ids)
        self.annotation.job_ids.update(collective_job_ids)
        if not self.cluster or not self.cluster.report(indent_level=1):
            result = False
        if self.validation and not self.validation.report(indent_level=1):
            result = False
        if not self.annotation or not self.annotation.report(indent_level=1):
            result = False
        if self.cluster.max_run_time is not None:
            self.max_run_time += self.cluster.max_run_time
            self.total_run_time += self.cluster.total_run_time
            self.avg_run_time += self.cluster.avg_run_time
        else:
            self.log_parse_error = True
        for stage in [self.validation, self.annotation]:
            if stage:
                if stage.max_run_time is not None:
                    self.max_run_time += stage.max_run_time
                    self.total_run_time += stage.total_run_time
                    self.avg_run_time += stage.avg_run_time
                else:
                    self.log_parse_error = True
        return result


def convert_set_to_ranges(input_set):
    """
    for a set of integers returns a list of consecutive ranges as strings

    Example:
        >>> convert_set_to_ranges({1, 2, 3, 7, 9, 10, 11})
        ['1-3', '7', '10-11']
    """
    ranges = []
    for curr in sorted(list(input_set)):
        if ranges:
            if ranges[-1][1] + 1 == curr:
                ranges[-1] = (ranges[-1][0], curr)
                continue
        ranges.append((curr, curr))
    result = []
    for start, end in ranges:
        if start == end:
            result.append(str(start))
        else:
            result.append(str(start) + '-' + str(end))
    return ', '.join(result)


def check_completion(target_dir, skipped_stages=None):
    """
    Args:
        target_dir (str): path to the main pipeline output directory
    """
    libraries = []
    summary = None
    pairing = None
    if not skipped_stages:
        skipped_stages = set()

    # check the library steps first
    for subdir in sorted(glob.glob(os.path.join(target_dir, '*'))):
        stage_name = os.path.basename(subdir)
        if stage_name == SUBCOMMAND.PAIR:
            pairing = PipelineStageRun(stage_name, subdir)
        elif stage_name == SUBCOMMAND.SUMMARY:
            summary = PipelineStageRun(stage_name, subdir)
        elif re.match(LIBRARY_DIR_REGEX, stage_name):
            libraries.append(LibraryRun(stage_name, subdir))
        else:
            log('ignoring dir', subdir)

    success_flag = True
    max_run_time = 0
    total_run_time = 0
    log_parse_error = False
    for lib in sorted(libraries, key=lambda x: x.name):
        log('checking library:', lib.name)
        if not lib.report():
            success_flag = False
        if lib.max_run_time:
            max_run_time += lib.max_run_time
            total_run_time += lib.total_run_time
        if lib.log_parse_error:
            log_parse_error = True

    if not pairing.report(time_stamp=True):
        success_flag = False
    if not summary.report(time_stamp=True):
        success_flag = False
    for stage in [summary, pairing]:
        if stage.max_run_time is not None:
            max_run_time += stage.max_run_time
            total_run_time += stage.total_run_time
        else:
            log_parse_error = True
    log(('' if not log_parse_error else 'min ') + 'parallel run time (s):', max_run_time)
    log(('' if not log_parse_error else 'min ') + 'total run time (s):', total_run_time)
    return success_flag
