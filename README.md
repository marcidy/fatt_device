## Repository
Each AMT FATT device has a branch on this repository.  'master' contains common code, but is not necessary a superset or a subset at this time.

### Branches
Each branch must have a README.md specific to the device for that branch.  We are going with a naming scheme like"<branch type>/<device name>" to identify the code running on devices at a glance.

#### Production branches
Once live, a device should be running a branch beginning with "prod/".  These are considered "master" for each device.  Device names should clearly identify the device type.  All prod branches should have the same workflows configured for consistency.

#### Branch names
All devices at this stage are being standardized, and since code can be replicated for devices without the need for a new branch, the code should not be per device, but per device type.

These are the only guidelines.  Quite frankly they may not prove useful over time as the scope of devices grow, but abstracting devices over how they function vs their label or physical installation point will significatly cutdown on maintentance.  If all doors need a firmware update, only one repo is updated.

"prod/door" or "prod/laser" is better than "prod/12345", since it's unclear what "12345" is at AMT.  

### Intra-branch Inheritence
A number of functions are common to many FATT devices.  This is currently unmanaged, but not yet large in number.  This means if something like 'report_attempt' in util.py is updated, that update must be manually moved to all branches.  This is not ideal.  As we grow the use cases and understand more what needs to be common to the devices, we can mange this as a library.

## Code conventions
Take the Zen of Python to the extreme: simple, explicit, and easy to understand beats clever, cute, and comlex.   Separate concerns fully soo each step is easy to digest.   Use verbose and explicit names.  There probably is not a strong need for anything more complex than object inheritence. 

## Installation
Installation instructions must be in a INSTALL.me file, and be complete.  Comlpete means every step required to run should be illustrated, including changes to the host OS.

Any required secrets must be mentioned in this file, but not defined.  No secrets (passwords, tokens, sensitive informaiton) should ever be stored in the repository. (Note: if a secret is accidentally commited, it will still be in the repository even if the file is removed from the branch.  Just tell someone, it's not a big deal, just has to be cleaned)

For example, if a device uses a token, that needs to be known.  The value of the token is a secret, however, and should not exist in the repo.

## Documentation
The code must be documented, and enough information must exist such that a relatively inexperienced person can understand, deploy, and update code.

## Tests
100% of test coverage is a good goal, but not always realistic.  However, all critical path code should have coverage that can at a mimimum detect change in output based on change in code.

pytest is an easy to use framework which simplifyes writing test cases
coverage is standard for measuring test coverage

Tests should be orders of magnitude more simple than the code they are testing.

### Mocking
A Mock is a fake object.  They are used in tests when using the real object is not possible, or causes more test complexity than is safe to use as a test case.  Python3 includes unittest.mock to assist with mocking, and should be understood before attempting to read or write unittests over hardware.

Since it's not possible to test hardware interaction directly when developping, all objects which interact with hardware should be mocked to provide a testable interface.  For example, if using a serial port, mocking lower-level read / write makes more sense when testing to make sure the control code paths are covered.  This will be the trickiest paradigm for folks new to coding or hardware, however, the laser is an example of this.  

