import sys
import os
import glob
import configparser
import subprocess
import shutil

current_desktop=os.environ.get('XDG_CURRENT_DESKTOP','')

class ParseError(Exception):
    pass
def print_usage():
    print('Usage:\n\tdetry e <file>\t\tExecute <file>\n\tdetry f <desktopFileId>\tFind the desktop file for <desktopFileId>\n\tdetry a\t\t\tShow autostart files\n\tdetry v\t\t\tVersion',file=sys.stderr)
def escape(s,esc,d):
    escaped=False
    s2=''
    for c in s:
        if escaped:
            if c in d:
                s2+=d[c]
            else:
                s2+=esc+c
            escaped=False
        elif c==esc:
            escaped=True
        else:
            s2+=c
    if escaped:
        s2+=esc
    return s2
def escape_value(s):
    return escape(s,'\\',{'s':' ','n':'\n','t':'\t','r':'\r','\\':'\\'})
def persent_expansion(s,d):
    return escape(s,'%',d)
def is_disabled(de):
    if 'Hidden' in de:
        return True
    if 'OnlyShowIn' in de:
        if current_desktop not in escape_value(de['OnlyShowIn']).rstrip(';').split(';'):
            return True
    if 'NotShowIn' in de:
        if current_desktop in escape_value(de['NotShowIn']).rstrip(';').split(';'):
            return True
    if 'TryExec' in de:
        if shutil.which(escape_value(de['TryExec'])) is None:
            return True
    return False
def parse_exec(s):
    quoted=False
    backslash=False
    a=''
    l=[]
    for c in s:
        if quoted:
            if backslash:
                if c in '\"`$\\':
                    a+=c
                else:
                    a+='\\'+c
                backslash=False
            elif c=='\\':
                backslash=True
            elif c=='\"':
                quoted=False
            else:
                a+=c
        else:
            if c=='\"':
                quoted=True
            elif c==' ':
                if a!='':
                    l+=[a]
                    a=''
            else:
                a+=c
    if quoted:
        raise ParseError
    if a!='':
        l+=[a]
    return l
def get_files(dirs):
    index=set()
    files=[]
    for d in dirs:
        if d[-1]!='/':
            d+='/'
        for f in glob.glob(d+'*.desktop'):
            if os.path.basename(f) in index:
                continue
            conf=configparser.ConfigParser(comment_prefixes=('#',),delimiters=('=',),interpolation=None)
            conf.read(f,encoding='utf-8')
            if 'Desktop Entry' not in conf:
                print(f'{f} [Desktop Entry] not found.',file=sys.stderr)
                continue
            de=conf['Desktop Entry']
            index.add(os.path.basename(f))
            if not is_disabled(de):
                files+=[f]
    return files
def get_autostart_files():
    return get_files([os.environ.get('XDG_CONFIG_HOME',os.path.expanduser('~/.config/autostart/'))]+os.environ.get('XDG_CONFIG_DIRS','/etc/xdg/autostart/').split(':'))
def get_desktop_files():
    dirs=[os.environ.get('XDG_DATA_HOME',os.path.expanduser('~/.local/share/'))]+os.environ.get('XDG_DATA_DIRS','/usr/local/share/:/usr/share/').split(':')
    dirs2=[]
    for d in dirs:
        if d[-1]!='/':
            d+='/'
        d+='applications/'
        dirs2+=[d]
    return get_files(dirs2)

args=sys.argv
argc=len(args)
if argc<2:
    print_usage()
    exit(1)
if args[1]=='e':
    if argc!=3:
        print_usage()
        exit(1)
    file=args[2]
    if not os.path.isfile(file):
        print(f'{file} does not exist.',file=sys.stderr)
        exit(1)
    conf=configparser.ConfigParser(comment_prefixes=('#',),delimiters=('=',),interpolation=None)
    conf.read(file,encoding='utf-8')
    if 'Desktop Entry' not in conf:
        print(f'{file} [Desktop Entry] not found',file=sys.stderr)
        exit(1)
    de=conf['Desktop Entry']
    if is_disabled(de):
        print(f'{file} is disabld.',file=sys.stderr)
        exit(1)
    if 'Exec' not in de:
        print(f'{file} Exec key not found.',file=sys.stderr)
        exit(1)
    try:
        l=parse_exec(escape_value(de['Exec']))
    except ParseError:
        print(f'{file} Exec key is invalid.',file=sys.stderr)
    l2=[]
    for s in l:
        if s=='%F' or s=='%U' or s=='%i':
            s=''
        else:
            s=persent_expansion(s,{'%':'%','f':'','u':'','c':'','k':''})
        if s!='':
            l2+=[s]
    if 'Terminal' in de and de['Terminal']=='true':
        if 'TERMINAL' in os.environ:
            l2=[os.environ['TERMINAL'],'-e']+l2
        else:
            print('Terminal=true but $TERMINAL is not defined',file=sys.stderr)
            exit(1)
    cwd=None
    if 'Path' in de:
        cwd=de['Path']
    subprocess.Popen(l2,cwd=cwd)
elif args[1]=='a':
    if argc!=2:
        print_usage()
        exit(1)
    for s in get_autostart_files():
        print(s)
elif args[1]=='f':
    if argc!=3:
        print_usage()
        exit(1)
    dfid=args[2]
    file=None
    for f in get_desktop_files():
        if dfid==os.path.basename(f):
            file=f
            break
    if file is None:
        print(f'{dfid} not found or disabled.',file=sys.stderr)
    print(file)
elif args[1]=='v':
    if argc!=2:
        print_usage()
        exit(1)
    print('detry-0.0.1')
else:
    print_usage()
    exit(1)
