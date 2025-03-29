import os
import ujson
import clock


def append_log(message):
    if 'log.txt' in os.listdir():
        file_size = os.stat('log.txt')[6]  # Get the file size in bytes
        if file_size > 100 * 1024:
            os.remove('log.txt')
    with open('log.txt', 'a') as f:
        timestamp = clock.get_current_time()
        log_line = f"{timestamp}: {message}"
        f.write(log_line + '\n')
    return log_line


def log(line):
    if isinstance(line, dict):
        line_str = ujson.dumps(line)
    else:
        line_str = str(line)
    print(line_str)
    log_line = append_log(line_str)
    return log_line
