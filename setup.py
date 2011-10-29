from distutils.core import setup

pkg = 'Extensions.AutoBackup'
setup (name = 'enigma2-plugin-extensions-autobackup',
       version = '0.1',
       description = 'AutoBackup',
       package_dir = {pkg: 'plugin'},
       packages = [pkg],
       package_data = {pkg: 
           ['plugin.png', 'backup.cfg', 'settings-backup.sh']}
      )
