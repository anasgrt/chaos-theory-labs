# frozen_string_literal: true

require "rbconfig"

vm_cpus = Integer(ENV.fetch("CHAOS_LABS_CPUS", "4"), 10)
vm_memory_mb = Integer(ENV.fetch("CHAOS_LABS_MEMORY_MB", "12288"), 10)
box_architecture = case RbConfig::CONFIG.fetch("host_cpu")
                   when "arm64", "aarch64" then "arm64"
                   when "x86_64", "amd64" then "amd64"
                   else abort "Unsupported host CPU architecture: #{RbConfig::CONFIG.fetch("host_cpu")}"
                   end

abort "CHAOS_LABS_CPUS must be at least 2" if vm_cpus < 2
abort "CHAOS_LABS_MEMORY_MB must be at least 12288" if vm_memory_mb < 12_288

Vagrant.configure("2") do |config|
  # Bento publishes native VirtualBox images for both arm64 and amd64.
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.box_version = "202502.21.0"
  config.vm.box_check_update = false
  config.vm.box_architecture = ENV.fetch("CHAOS_LABS_ARCH", box_architecture)
  config.vm.hostname = "chaos-labs"
  config.vm.boot_timeout = 600

  # Labs and Docker data must live on the Linux filesystem. macOS shared folders
  # alter ownership, I/O, and filesystem behaviour that several labs measure.
  config.vm.synced_folder ".", "/vagrant", disabled: true
  # This pinned box supplies a 64 GiB virtual disk. Its LVM root volume is
  # expanded by ansible/playbook.yml; the VirtIO SCSI controller is not
  # resizable through Vagrant's VirtualBox disk capability.

  # There is intentionally no Vagrant provisioner. Run ansible/run.sh after
  # vagrant up so VM creation and software configuration remain independent.
  config.vm.provider "virtualbox" do |vb|
    vb.name = "chaos-labs"
    vb.cpus = vm_cpus
    vb.memory = vm_memory_mb
    vb.gui = false
  end
end
