import os

def find_account_directory(platform_directory, account_id):
    """アカウントIDを含むディレクトリを検索"""
    try:
        if not os.path.exists(platform_directory):
            raise Exception(f"監視ディレクトリが存在しません: {platform_directory}")
        
        for dirname in os.listdir(platform_directory):
            dir_path = os.path.join(platform_directory, dirname)
            
            if os.path.isdir(dir_path):
                if '_' in dirname:
                    id_part = dirname.split('_')[0]
                else:
                    id_part = dirname
                
                if id_part == account_id:
                    return dir_path
        
        raise Exception(f"アカウントID {account_id} のディレクトリが見つかりません")
        
    except Exception as e:
        print(f"ディレクトリ検索エラー: {str(e)}")
        raise