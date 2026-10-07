#!/bin/sh
# nvidia.cublas.lib and nvidia.cudnn.lib are namespaces: __file__ is None, so go through __path__.
LIBS=$(python -c "import nvidia.cublas.lib, nvidia.cudnn.lib; print(list(nvidia.cublas.lib.__path__)[0] + ':' + list(nvidia.cudnn.lib.__path__)[0])")
export LD_LIBRARY_PATH="$LIBS${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$@"
