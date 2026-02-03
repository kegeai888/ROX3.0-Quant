# dmgbuild configuration file
import os

# 软件名称
filename = 'RoxQuant.dmg'
volume_name = 'RoxQuant'

# 打包内容：将 RoxQuant.app 放入根目录
# 以及一个快捷方式到 Applications
deploy_dir = os.path.join(os.getcwd(), 'dist')
app_path = os.path.join(deploy_dir, 'RoxQuant.app')

files = [app_path]

symlinks = { 'Applications': '/Applications' }

# 窗口设置
window_rect = ((100, 100), (500, 300))
background = 'builtin-arrow'

# 图标设置
icon_locations = {
    'RoxQuant.app': (140, 120),
    'Applications': (360, 120)
}

# 图标大小
icon_size = 128
