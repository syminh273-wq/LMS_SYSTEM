from django.urls import path
from features.social.viewsets.post_viewset import (
    FeedView, FollowingFeedView, MyPostsView, UserPostsView,
    PostListCreateView, PostDetailView,
    PostLikeView, PostCommentView, PostCommentDeleteView,
)
from features.social.viewsets.follow_viewset import (
    FollowToggleView, FollowingListView, FollowersListView, FollowStatusView
)

urlpatterns = [
    # Posts & Feed
    path('feed/',                                  FeedView.as_view(),              name='social-feed'),
    path('feed/following/',                        FollowingFeedView.as_view(),      name='social-feed-following'),
    path('posts/',                                 PostListCreateView.as_view(),     name='social-posts'),
    path('posts/mine/',                            MyPostsView.as_view(),            name='social-my-posts'),
    path('posts/user/<str:consumer_uid>/',         UserPostsView.as_view(),          name='social-user-posts'),
    path('posts/<str:uid>/',                       PostDetailView.as_view(),         name='social-post-detail'),
    path('posts/<str:uid>/like/',                  PostLikeView.as_view(),           name='social-post-like'),
    path('posts/<str:uid>/comments/',              PostCommentView.as_view(),        name='social-post-comments'),
    path('posts/<str:uid>/comments/<str:cuid>/',   PostCommentDeleteView.as_view(),  name='social-comment-delete'),

    # Following
    path('follow/<str:target_uid>/',               FollowToggleView.as_view(),       name='social-follow-toggle'),
    path('follow/status/<str:target_uid>/',        FollowStatusView.as_view(),       name='social-follow-status'),
    path('following/',                             FollowingListView.as_view(),      name='social-following-list'),
    path('followers/',                             FollowersListView.as_view(),      name='social-followers-list'),
]
