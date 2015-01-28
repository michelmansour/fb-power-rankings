from setuptools import setup

setup(name='fbpowerrankings',
      version='0.1',
      description='Fantasy baseball power rankings',
      url='http://github.com/michelmansour/fb-power-rankings',
      author='Michel Mansour',
      license='MIT',
      package=['fbpowerrankings'],
      install_requires=['requests==2.5.1',
                        'Jinja2==2.7.3',
                        'lxml==3.4.1',
                        'beautifulsoup4==4.3.2'],
      zip_safe=False)
