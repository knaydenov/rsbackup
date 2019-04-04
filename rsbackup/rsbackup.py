import argparse
import yaml
import os
import logging
import subprocess
import sys
from jsonschema import validate
from datetime import datetime


def dir_abspath(dirname):
    return os.path.abspath(os.path.realpath(os.path.expanduser(dirname)))


class RSBackup(object):
    LOG_FORMAT = '%(levelname) -10s %(asctime)s %(name) -30s %(funcName) ' '-35s %(lineno) -5d: %(message)s'
    schema = {
        "type": "array",
        "additionalProperties": {
            "type": "object",
            "required": ["destination"],
            "properties": {
                "source": {
                    "type": "string"
                },
                "destination": {
                    "type": "string"
                },
                "archive": {
                    "type": "boolean"
                },
                "include": {
                    "type": "object",
                    "additionalProperties": {"type": "boolean"}
                },
                "delete": {
                    "type": "boolean"
                }
            }
        }
    }

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._args = None
        self._parser = argparse.ArgumentParser(description='Backup tool')
        self._yaml = None
        self._source = None
        self._destination = None
        self._dry_run = True
        self._current_dir = None
        self._rsync = None
        self._archive = True
        self._include = {}
        self._delete = False

    def exec(self):
        self._parser.add_argument('config_path', nargs='?', default='.rsbu.yaml')
        self._parser.add_argument('--force', action='store_true')
        self._parser.add_argument('-v', '--verbose', dest='verbose_count', action='count', default=0, help='increases log verbosity for each occurence.')

        self._args = self._parser.parse_args()

        logging.basicConfig(level=(max(3 - self._args.verbose_count, 0) * 10), format=self.LOG_FORMAT)

        self.read_config()

        self.change_current_dir()

        for i in range(len(self._yaml)):
            self.configure(self._yaml[i])
            self.create_destination_dir()
            self.build_rsync()
            self.run()

            if self._args.verbose_count >= 1:
                print(self._rsync)
                print('==================================================')

    def change_current_dir(self):
        self._current_dir = os.path.dirname(os.path.realpath(self._args.config_path))
        os.chdir(self._current_dir)

    def create_destination_dir(self):
        if not self._dry_run:
            if not os.path.isdir(self._destination):
                try:
                    os.makedirs(self._destination)
                except os.error:
                    raise Exception("Destination directory '%s' does not exist and can not be created." % self._destination)

    def configure(self, current_yaml):
        self._source = dir_abspath(current_yaml['source'] if 'source' in current_yaml else '.')
        if not os.path.isdir(self._source):
            raise Exception("Source directory '%s' does not exist" % self._source)

        self._destination = dir_abspath(current_yaml['destination'] if 'destination' in current_yaml else '.')

        if self._args.force:
            self._dry_run = False

        if 'archive' in current_yaml:
            self._archive = current_yaml['archive']
        else:
            self._archive = True

        if 'include' in current_yaml:
            self._include = current_yaml['include']
        else:
            self._include = {}

        if 'delete' in current_yaml:
            self._delete = current_yaml['delete']
        else:
            self._delete = False

    def read_config(self):
        with open(self._args.config_path, 'r') as stream:
            try:
                data = yaml.load(stream, yaml.SafeLoader)
                validate(data, self.schema)
                self._yaml = data
            except yaml.YAMLError as exc:
                self._logger.error(exc)

    def build_filters(self):
        filters = []

        for path, should_include in self._include.items():
            if not should_include:
                filters.append("- %s/***" % path)

        for path, should_include in self._include.items():
            if should_include:
                parts = path.split("/")
                for i in range(len(parts)):
                    filters.append("+ %s/" % "/".join(parts[0:i]))
                filters.append("+ %s/***" % "/".join(parts))

        if len(filters):
            filters.append("- *")

        return filters

    def build_rsync(self):
        rsync = ['rsync']
        options = []

        if self._dry_run:
            rsync.append("--dry-run")

        for f in self.build_filters():
            rsync.append("--filter='%s'" % f)

        if self._delete:
            rsync.append("--delete")
            rsync.append("--backup")
            rsync.append("--backup-dir='.recycled_%s'" % datetime.now().strftime("%d_%m_%Y__%H_%M_%S"))

        if self._args.verbose_count >= 2:
            options.append('v')
            options.append('P')

        if self._archive:
            options.append('a')

        if len(options):
            rsync.append("-%s" % (''.join(options)))

        rsync.append("%s/" % self._source)
        rsync.append("%s/" % self._destination)

        self._rsync = ' '.join(rsync)

    def run(self):
        with subprocess.Popen(self._rsync, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as rsync:
            while True:
                next_line = rsync.stdout.readline().decode("utf-8")
                if not next_line:
                    break

                sys.stdout.write(next_line)


def main():
    rs_backup = RSBackup()
    rs_backup.exec()




