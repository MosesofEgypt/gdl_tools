# hack to allow running within import dir
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
