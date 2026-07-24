from django.urls import path
from features.social.viewsets.post_viewset import (
    FeedView, FollowingFeedView, MyPostsView, UserPostsView,
    PostListCreateView, PostDetailView,
    PostLikeView, PostCommentView, PostCommentDeleteView,
)
from features.social.viewsets.post_image_viewset import PostImageUploadView
from features.social.viewsets.follow_viewset import (
    FollowToggleView, FollowingListView, FollowersListView, FollowStatusView
)
from features.social.viewsets.classroom_favorite_viewset import (
    ClassroomFavoriteToggleView, ClassroomFavoriteStatusView, ClassroomFavoriteListView,
)
from features.social.viewsets.profile_viewset import (
    MyProfileView, PublicProfileView,
    ProfileAvatarUploadView, ProfileCoverUploadView,
)
from features.social.viewsets.suggestions_viewset import SuggestedUsersView

urlpatterns = [
    # Posts & Feed
    path('feed/',                                  FeedView.as_view(),              name='social-feed'),
    path('feed/following/',                        FollowingFeedView.as_view(),      name='social-feed-following'),
    path('posts/',                                 PostListCreateView.as_view(),     name='social-posts'),
    path('posts/upload-images/',                   PostImageUploadView.as_view(),    name='social-post-upload-images'),
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

    # Profile (Community Workspace)
    path('profile/me/',                            MyProfileView.as_view(),                  name='social-profile-me'),
    path('profile/me/avatar/',                     ProfileAvatarUploadView.as_view(),        name='social-profile-avatar'),
    path('profile/me/cover/',                      ProfileCoverUploadView.as_view(),         name='social-profile-cover'),
    path('profile/<str:owner_id>/',                PublicProfileView.as_view(),              name='social-profile-public'),

    # Classroom favorites
    path('classrooms/favorites/',                  ClassroomFavoriteListView.as_view(),  name='social-classroom-favorites'),
    path('classrooms/<str:classroom_uid>/favorite/',         ClassroomFavoriteToggleView.as_view(), name='social-classroom-favorite'),
    path('classrooms/<str:classroom_uid>/favorite/status/',  ClassroomFavoriteStatusView.as_view(), name='social-classroom-favorite-status'),

    # Suggestions
    path('suggestions/',                           SuggestedUsersView.as_view(),          name='social-suggestions'),
]
