#!/usr/bin/python3
# Auto-tuner prototype
# Built for INE5540 robot overlords

import subprocess # to run stuff
import sys # for args, in case you want them
import time # for time
import timeit

def gcc(flags):
    def compile_it(executable, source_code):
        return ['gcc','-o', executable, source_code] + flags
    return compile_it 
    
def clang(flags):
    def compile_it(executable, source_code):
        return ['clang','-o', executable, source_code] + flags
    return compile_it 
    
def icc(flags):
    def compile_it(executable, source_code):
        return ['icc','-o', executable, source_code] + flags
    return compile_it 

def tuner(argv, step, compiler):
    exec_file = 'matmult'
    compilation_line = compiler(exec_file, "mm.c")
    steps = ['-DSTEP={}'.format(step)]

    # Compile code
    compilation_try = subprocess.call(compilation_line+steps, stdout=subprocess.PIPE)
    if (compilation_try != 0):
        return {
            "exit_code": compilation_try
        }

    # Run code
    input_size = 4
    code = "subprocess.call(['./{}', '{}'], stdout=subprocess.PIPE)".format(exec_file, input_size)
    run_trial = eval(code, {}, {"subprocess": subprocess})
    if run_trial == 0:
    #t_begin = time.time() # timed run
        timer = timeit.timeit(code, "import subprocess", number=100)
    else:
        timer = float('inf')
    # t_end = time.time()
    return {
        "time": timer,
        "exit_code": run_trial
    }


if __name__ == "__main__":
    gcc_params = [["-mtune=native"], 
        ["-ftree-loop-distribution"], ["-ftree-parallelize-loops=2"],
        ["-ftree-parallelize-loops=4"], ["-funroll-loops"]]
    compilation_flags = {
        gcc: [["-O1"], ["-O2"], ["-O3"], ["-Ofast"]]+[param1+param2 for i1, param1 in enumerate(gcc_params) for i2, param2 in enumerate(gcc_params) if i1 < i2]+gcc_params,
        clang: [["-O1"], ["-O2"], ["-O3"], ["-Ofast"]],
        icc: [["-O1"], ["-O2"], ["-O3"], ["-Ofast"], ["-xHost"], ["-parallel"]]
    }
    compilers = [gcc, clang, icc]
    all_executions = {}
    for step in range(1, 10): 
        executions = []
        for compiler in compilers:
            for compilation_flag in compilation_flags[compiler]:
                result = tuner(sys.argv[1:], step, compiler(compilation_flag))
                executions.append({
                    "time": result["time"], # go auto-tuner
                    "exit_code": result["exit_code"],
                    "flags": compilation_flag,
                    "compiler": compiler,
                    "step": step
                })
        executions.sort(key=lambda item: item["time"])
        first = False
        for position, execution in enumerate(executions, start=1):
            if execution["exit_code"] != 0:
                continue
            if not first:
                print("- STEP={}:".format(step)) 
                first = True
            print("\t{}) compiler: {} - flags: {} - time: {}s - {}".format(position, execution["compiler"].__name__, " ".join(execution["flags"]), execution["time"], "OK" if execution["exit_code"] == 0 else "FAIL"))
            all_executions[position] = all_executions.get(position, [])
            all_executions[position].append(execution)
    print("Report: ")
    for compiler in compilers:
        for compilation_flag in compilation_flags[compiler]:
            min_position = float("inf")
            for position, executions in all_executions.items():
                found = False
                for execution in executions:
                    if execution["compiler"] == compiler and execution["flags"] == compilation_flag:
                        found = True 
                        break 
                if found and min_position > position:
                    min_position = position 
            max_position = float("-inf")
            for position, executions in all_executions.items():
                found = False
                for execution in executions:
                    if execution["compiler"] == compiler and execution["flags"] == compilation_flag:
                        found = True 
                        break 
                if found and max_position < position:
                    max_position = position 
            frequencies = {}
            frequent_position = {
                "position": None,
                "count": -1
            }
            for position, executions in all_executions.items():
                count = 0
                for execution in executions:
                    if execution["compiler"] == compiler and execution["flags"] == compilation_flag:
                        count += 1
                if count > 0:
                    frequencies[position] = frequencies.get(position, 0) + count
                    if frequencies[position] > frequent_position["count"]:
                        frequent_position["count"] = frequencies[position]
                        frequent_position["position"] = position
            print("\t- compiler: {} - flags: {} - minimal position: {} - maximum position: {} - frequent position: {} ({} times)".format(compiler.__name__, " ".join(compilation_flag), min_position, max_position, frequent_position["position"], frequent_position["count"]))

    