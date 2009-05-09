require 'rubygems'

require 'date'
require 'rake'
require 'rake/clean'
require 'rake/packagetask'

module Ccx2
   VERSION = '0.2.0'
end

VERSION_FILE_CONTENTS = %Q{
__version__ = '%s'
}

CLEAN.include("build")

def write_version_file(v)
   File.open("src/ccx2/__init__.py", "w") do |f|
      f.puts(VERSION_FILE_CONTENTS % v)
   end
end

desc "Clean and repackage dev version"
task :default => [ :clean, :versiondev, :repackage ]

desc "Generate version file"
task :version do
   write_version_file(Ccx2::VERSION)
end

desc "Generate git aware version file"
task :versiondev do
   if File.directory?('.git')
      commit = `git log -1 --pretty=format:%h`.chomp
      branch = `git branch`.split("\n").grep(/^\*/).first
      branch.chomp! if branch
      branch = (branch.gsub(/^\* /, '') if branch && !branch.empty? && branch != "* master") || nil
      additional = "#{'-'+branch if branch}#{'-'+commit if commit}"
      additional = "-git-#{Date.today.strftime('%Y%m%d')}#{additional}" if additional
   end
   write_version_file("#{Ccx2::VERSION}#{additional}")
end

desc "Prepare for release"
task :release => [:clean, :version, :repackage]

Rake::PackageTask.new("ccx2", Ccx2::VERSION) do |pkg|
   pkg.package_dir = "build"
   pkg.package_files = ["LICENSE", "LICENSE.urwid", "README.mkd", "setup.py"] + \
                       Dir["scripts/*"] + \
                       Dir["src/*.py"] + \
                       Dir["src/**/*.py"]
   pkg.need_tar_gz = true
end

