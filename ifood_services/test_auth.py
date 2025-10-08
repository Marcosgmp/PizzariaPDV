from auth import IfoodAuthService

if __name__ == "__main__":
    auth = IfoodAuthService()
    token = auth.get_token()
    print("\n🔍 Token recebido:")
    print(token)
