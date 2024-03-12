import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='proflame_wifi',
    author='Kevin Lucas',
    author_email='dev@kitsune.bi',
    description='Basic client for interacting with Proflame wifi enabled gas fireplaces',
    keywords='home_automation, smart_home, pypi, package',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Pharrox/proflame-wifi',
    project_urls={
        'Documentation': 'https://github.com/Pharrox/proflame-wifi',
        'Bug Reports': 'https://github.com/Pharrox/proflame-wifi/issues',
        'Source Code': 'https://github.com/Pharrox/proflame-wifi',
        'Funding': 'https://www.buymeacoffee.com/pharrox',
        # 'Say Thanks!': '',
    },
    package_dir={'': 'src'},
    packages=setuptools.find_packages(where='src'),
    classifiers=[
        # see https://pypi.org/classifiers/
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.11',
    install_requires=['websockets>=12.0'],
    extras_require={
        'dev': ['check-manifest'],
        'test': [
            'coverage',
            'pytest-cov',
        ],
    },
    entry_points={
        'console_scripts': [
            'proflame-get=proflame_wifi.get_state:main',
            'proflame-set=proflame_wifi.set_state:main',
        ],
    },
)