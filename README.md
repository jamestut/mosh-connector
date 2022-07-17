# Mosh Connector

There are three important components in [Mosh](https://github.com/mobile-shell/mosh):

- `mosh-server` is the one that runs on the remote host and is responsible for hosting the terminals.
- `mosh-client` is the one that runs on the interactive local machine (e.g. a machine actively used by a user such as laptops or workstations), and is responsible for displaying the terminal from a `mosh-server`. The `mosh-client` communicates to `mosh-server` directly using UDP over IPv4 and **not** over SSH.
- `mosh` is a Perl script that runs on the same computer as the `mosh-client`. It is responsible for starting the `mosh-server` **over SSH**, and then starting the `mosh-client` locally.

This Python 3 script is intended as a drop-in replacement for the third component: `mosh`. The most important feature of this script is that it uses the vanilla `ssh` commands directly. This means that if you have `ControlMaster` enabled, it will work too, resulting in a much faster (almost instantenous) startup time of your Mosh session!
