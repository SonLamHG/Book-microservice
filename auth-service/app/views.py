from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .serializers import UserSerializer
from .jwt_utils import generate_token, verify_token


class Register(APIView):
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role', 'CUSTOMER')

        if not username or not email or not password:
            return Response({'error': 'username, email and password are required'},
                            status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'},
                            status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        user.save()

        token = generate_token(user.id, user.username, user.role)
        return Response({
            'token': token,
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class Login(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'},
                            status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({'error': 'Invalid credentials'},
                            status=status.HTTP_401_UNAUTHORIZED)

        token = generate_token(user.id, user.username, user.role)
        return Response({
            'token': token,
            'user': UserSerializer(user).data,
        })


class VerifyToken(APIView):
    def post(self, request):
        token = request.data.get('token', '')
        if not token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

        payload = verify_token(token)
        if payload is None:
            return Response({'error': 'Invalid or expired token'},
                            status=status.HTTP_401_UNAUTHORIZED)
        return Response({'valid': True, 'user': payload})


class UserList(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)


class ChangePassword(APIView):
    def put(self, request):
        user_id = request.data.get('user_id')
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not all([user_id, old_password, new_password]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_password(old_password):
            return Response({'error': 'Incorrect old password'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)


def health_check(request):
    from django.http import JsonResponse
    return JsonResponse({'status': 'healthy', 'service': 'auth-service'})
