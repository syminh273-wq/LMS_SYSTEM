from django.shortcuts import render

def test_chat_view(request, room_name='lobby'):
    return render(request, 'test_chat.html', {
        'room_name': room_name
    })
