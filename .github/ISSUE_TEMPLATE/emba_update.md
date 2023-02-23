---
name: EMBA upgrade
about: Requirements for EMBA upgrade
title: ''
labels: 'EMBA'
assignees: ''

---

**EMBA upgrade**
The EMBA version was upgraded to release XXX

**Steps**
[ ] Running EMBArk installation (default mode/dev mode) (has to be from a previous working build)
[ ] Create a new branch on your own forked repository.
[ ] Update the EMBA submodule: `cd emba ; git checkout <NEW_RELEASE>`
[ ] Restart the Server `sudo ./run-server.sh`
[ ] Test operation: 
    - [ ]Test 1 firmware with default scan
        - [ ]Check all Result-Pages
    - [ ]Test 1 firmware with with different scan-options (modules / flags)
        - [ ]Check all Result-Pages
        - [ ]Validate the inputs with the final emba-command
    - [ ]Export both zip-files
        -[ ]check for any formatting or other issues
[ ] Commit it `git add emba ; git commit -m "upgrade to release <NEW_RELEASE>"`
[ ] Open the Pull Request


**Screenshots**
Add some pictures of the results to prove the server behaves as expected.

**OS**
 ubuntu server / desktop

**Additional context**
Add any other context about the problem here.
