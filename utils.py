import os

def find_account_directory(platform_directory, account_id):
    """アカウントIDを含むディレクトリを検索・作成"""
    try:
        if not os.path.exists(platform_directory):
            # ディレクトリが存在しない場合は作成
            account_dir = os.path.join(platform_directory, f"{account_id}_user")
            os.makedirs(account_dir, exist_ok=True)
            return account_dir
        
        # 既存のディレクトリから検索
        for dirname in os.listdir(platform_directory):
            dir_path = os.path.join(platform_directory, dirname)
            if os.path.isdir(dir_path):
                if '_' in dirname:
                    id_part = dirname.split('_')[0]
                else:
                    id_part = dirname
                
                if id_part == account_id:
                    return dir_path
        
        # 見つからない場合は作成
        account_dir = os.path.join(platform_directory, f"{account_id}_user")
        os.makedirs(account_dir, exist_ok=True)
        return account_dir
        
    except Exception as e:
        print(f"ディレクトリ検索エラー: {str(e)}")
        raise