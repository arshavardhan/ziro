import config

def docker_command(root,name):
    return ['docker','run','--name',name,'--rm','--pull=never','--network=none','--read-only',
        '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=512m','--cpus=1',
        '--user=65534:65534','--tmpfs=/tmp:rw,noexec,nosuid,size=32m',
        '--mount',f'type=bind,source={root.resolve()},target=/repo,readonly','-w','/repo',
        '-e','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1','-e','PYTHONDONTWRITEBYTECODE=1',
        '-e','OPENBLAS_NUM_THREADS=1','-e','OMP_NUM_THREADS=1',config.TEST_IMAGE,
        'python','-m','pytest','-q','-o','addopts=','-p','no:cacheprovider','--junitxml=/tmp/results.xml']
