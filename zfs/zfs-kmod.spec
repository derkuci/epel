%bcond_with     debug
%bcond_with     debuginfo
%global kernel_version_tilde %(rpm -q --qf '-%%{VERSION}-%%{RELEASE}' kernel-devel | grep ^- | tr - \\\~)
%global kernel_module_package_buildreqs kernel-devel kernel-abi-stablelists redhat-rpm-config kernel-rpm-macros elfutils-libelf-devel kmod
%global kmodtool_generate_buildreqs 1

Name:           zfs-kmod
Version:        2.2.6
Release:        1%{?kernel_version_tilde}

Summary:        Kernel module(s)
Group:          System Environment/Kernel
License:        CDDL
URL:            https://github.com/openzfs/zfs
BuildRequires:  %kernel_module_package_buildreqs
Source0:        https://github.com/openzfs/zfs/releases/download/zfs-%{version}/zfs-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

# Additional dependency information for the kmod sub-package must be specified
# by generating a preamble text file which kmodtool can append to the spec file.
%(/bin/echo -e "\
Requires:       zfs = %{version}\n\
Conflicts:      zfs-dkms" > %{_sourcedir}/kmod-preamble)

# LDFLAGS are not sanitized by arch/*/Makefile for these architectures.
%ifarch ppc ppc64 ppc64le aarch64
%global __global_ldflags %{nil}
%endif

%description
This package contains the ZFS kernel modules.

%define kmod_name zfs

%kernel_module_package -n %{kmod_name} -p %{_sourcedir}/kmod-preamble

%define ksrc %{_usrsrc}/kernels/%{kverrel}
%define kobj %{ksrc}

%package -n kmod-%{kmod_name}-devel
Summary:        ZFS kernel module(s) devel common
Group:          System Environment/Kernel

%description -n  kmod-%{kmod_name}-devel
This package provides the header files and objects to build kernel modules.

%prep
if ! [ -d "%{ksrc}"  ]; then
        echo "Kernel build directory isn't set properly, cannot continue"
        exit 1
fi

%if %{with debug}
%define debug --enable-debug
%else
%define debug --disable-debug
%endif

%if %{with debuginfo}
%define debuginfo --enable-debuginfo
%else
%define debuginfo --disable-debuginfo
%endif

%setup -n %{kmod_name}-%{version}
%build
%configure \
        --with-config=kernel \
        --with-linux=%{ksrc} \
        --with-linux-obj=%{kobj} \
        %{debug} \
        %{debuginfo} \
        %{?kernel_cc} \
        %{?kernel_ld} \
        %{?kernel_llvm}
make %{?_smp_mflags}

# Module signing (modsign)
#
# This must be run _after_ find-debuginfo.sh runs, otherwise that will strip
# the signature off of the modules.
# (Based on Fedora's kernel.spec workaround)
%define __modsign_install_post \
        sign_pem="%{ksrc}/certs/signing_key.pem"; \
        sign_x509="%{ksrc}/certs/signing_key.x509"; \
        if [ -f "${sign_x509}" ]\
        then \
            echo "Signing kernel modules ..."; \
            for kmod in $(find %{buildroot}/lib/modules/%{kverrel}/extra/ -name \*.ko); do \
                    %{ksrc}/scripts/sign-file sha256 ${sign_pem} ${sign_x509} ${kmod}; \
            done \
        fi \
%{nil}

# hack to ensure signing happens after find-debuginfo.sh runs
%define __spec_install_post \
        %{?__debug_package:%{__debug_install_post}}\
        %{__arch_install_post}\
        %{__os_install_post}\
        %{__modsign_install_post}

%install
make install \
        DESTDIR=${RPM_BUILD_ROOT} \
        INSTALL_MOD_DIR=extra/%{kmod_name}
%{__rm} -f %{buildroot}/lib/modules/%{kverrel}/modules.*

# find-debuginfo.sh only considers executables
%{__chmod} u+x  %{buildroot}/lib/modules/%{kverrel}/extra/*/*

%clean
rm -rf $RPM_BUILD_ROOT

%files -n kmod-%{kmod_name}-devel
%{_usrsrc}/%{kmod_name}-%{version}
