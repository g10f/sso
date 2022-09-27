import multiprocessing
secure_scheme_headers = {'X-FORWARDED-SSL': 'on', 'X-FORWARDED-PROTO': 'https'}
workers = multiprocessing.cpu_count() * 2 + 1
bind = "0.0.0.0:8000"
forwarded_allow_ips = '*'
