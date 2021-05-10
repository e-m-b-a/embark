from boundedExecutor import boundedExecutor


boundExecutor = boundedExecutor(bound=2, max_workers=2)

boundExecutor.submit(boundExecutor.run_shell_cmd, "./../../emba/scratch.sh")
