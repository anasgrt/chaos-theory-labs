# frozen_string_literal: true

require "rbconfig"

box_architecture = case RbConfig::CONFIG.fetch("host_cpu")
                   when "arm64", "aarch64" then "arm64"
                   when "x86_64", "amd64", "x64" then "amd64"
                   else abort "Unsupported host CPU architecture: #{RbConfig::CONFIG.fetch("host_cpu")}"
                   end

Vagrant.configure("2") do |config|
  # Bento publishes native VirtualBox images for both arm64 and amd64.
  config.vm.box = "bento/ubuntu-24.04"
  config.vm.box_version = "202502.21.0"
  config.vm.box_check_update = false
  config.vm.box_architecture = ENV.fetch("CHAOS_LABS_ARCH", box_architecture)
  config.vm.boot_timeout = 600

  # Labs and Docker data must live on the Linux filesystem. macOS shared folders
  # alter ownership, I/O, and filesystem behaviour that several labs measure.
  config.vm.synced_folder ".", "/vagrant", disabled: true
  # This pinned box supplies a 64 GiB virtual disk. Its LVM root volume is
  # expanded by ansible/provision.yml; the VirtIO SCSI controller is not
  # resizable through Vagrant's VirtualBox disk capability.

  # Provision once. Lab setup/reset only changes resources inside this VM.
  config.vm.define "chaos", primary: true do |vm|
    vm.vm.hostname = "chaos-labs"
    vm.vm.provider "virtualbox" do |vb|
      vb.name = "chaos-labs"
      vb.cpus = 4
      vb.memory = 16_384
      vb.gui = false
    end
  end
end
