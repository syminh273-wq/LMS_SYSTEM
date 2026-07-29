import base64
import json
import uuid

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.serializers.classroom import ClassroomResponseSerializer
from core.serializers.classroom.request import ClassroomRequestSerializer
from core.views.api.base_viewset import BaseModelViewSet
from core.views.mixins import SpaceScopeMixin
from features.chat.serializers.conversation_serializer import ConversationSerializer
from features.chat.services.conversation_service import ConversationService
from features.course.classroom.services import Service
from features.course.classroom.services.classroom_doc_service import ClassroomDocService
from features.course.classroom.services.classroom_activity_log_service import ClassroomActivityLogService
from features.resource.serializers.resource_response_serializer import ResourceResponseSerializer

class SpaceClassroomViewSet(SpaceScopeMixin, BaseModelViewSet):
    serializer_class = ClassroomResponseSerializer

    def get_queryset(self):
        return Service().get_by_teacher(self.request.user.uid)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = Service().find(kwargs['uid'])
        return Response(ClassroomResponseSerializer(instance).data)

    def create(self, request, *args, **kwargs):
        serializer = ClassroomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Service().create_classroom(
            teacher_id=request.user.uid,
            data=serializer.validated_data,
        )
        ClassroomActivityLogService().log(
            classroom_uid=instance.uid,
            log_level='major',
            event_type='classroom_created',
            actor_id=request.user.uid,
            actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
            actor_role='teacher',
            target_name=instance.name,
        )
        return Response(ClassroomResponseSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])

        # Ownership check
        if instance.teacher_id != request.user.uid:
            raise PermissionDenied("You do not have permission to update this classroom.")

        serializer = ClassroomRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = service.update(instance, **serializer.validated_data)
        return Response(ClassroomResponseSerializer(instance).data)

    def destroy(self, request, *args, **kwargs):
        service = Service()
        instance = service.find(kwargs['uid'])

        # Ownership check
        if instance.teacher_id != request.user.uid:
            raise PermissionDenied("You do not have permission to delete this classroom.")

        service.delete(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def conversation(self, request, uid=None):
        """Return (or auto-create) the channel conversation for this classroom."""
        conv = ConversationService().get_or_create_channel(
            classroom_uid=uuid.UUID(str(uid)),
            created_by_id=request.user.uid,
        )
        return Response(ConversationSerializer(conv).data)

    @action(detail=True, methods=['get'])
    def sharing_link(self, request, uid=None):
        classroom = Service().find(uid)
        return Response({
            'code': classroom.pid,
            'url': f'/join/{classroom.pid}',
        })


    def docs_upload(self, request, uid=None):
        """
        Upload a document for a classroom.
        @param file: uploaded document, PDF/TXT/MD (required)
        @param section: category label (optional)
        @param folder_id: destination folder uid (optional)
        @param order_index: position within folder (optional)
        @return: created document
        """
        if 'file' not in request.FILES:
            return Response(
                {'success': False, 'message': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        section = request.data.get('section', '')
        folder_id = request.data.get('folder_id') or None
        exam_period = request.data.get('exam_period') or None
        try:
            order_index = int(request.data.get('order_index', 0))
        except (TypeError, ValueError):
            order_index = 0
        result = ClassroomDocService().upload_and_index(
            classroom_uid=str(uid),
            file_obj=request.FILES['file'],
            section=section,
            folder_id=folder_id,
            order_index=order_index,
            exam_period=exam_period,
        )
        resource = result.get('data')
        if resource:
            ClassroomActivityLogService().log(
                classroom_uid=uid,
                log_level='major',
                event_type='document_uploaded',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_name=getattr(resource, 'name', ''),
                metadata={'section': section, 'folder_id': str(folder_id) if folder_id else ''},
            )
            resp_data = ResourceResponseSerializer(resource).data
            if not result.get('success'):
                resp_data['_warning'] = result.get('message', 'LanceDB indexing thất bại')
            return Response(resp_data, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def docs_list(self, request, uid=None):
        """
        List documents for a classroom.
        @param section: category label (optional)
        @param folder_id: filter folder uid (optional)
        @return: list of documents
        """
        section = request.query_params.get('section')
        folder_id = request.query_params.get('folder_id') or None
        if folder_id or 'folder_id' in request.query_params:
            docs = ClassroomDocService().list_folder(classroom_uid=str(uid), folder_id=folder_id)
        else:
            docs = ClassroomDocService().list_docs(classroom_uid=str(uid), section=section)
        return Response(ResourceResponseSerializer(docs, many=True).data)

    @action(detail=True, methods=['get'], url_path='docs/tree')
    def docs_tree(self, request, uid=None):
        """
        List the folder tree and root-level documents for a classroom.
        @return: folders, root-level docs, preview folder uid
        """
        from features.resource.serializers.resource_folder_serializer import ResourceFolderTreeSerializer
        tree = ClassroomDocService().list_tree(classroom_uid=str(uid))
        return Response({
            'folders': ResourceFolderTreeSerializer(tree['folders'], many=True).data,
            'docs_root': ResourceResponseSerializer(tree['docs_root'], many=True).data,
            'preview_folder_uid': str(tree['preview_folder'].uid) if tree.get('preview_folder') else None,
        })

    @action(detail=True, methods=['post'], url_path='docs/reorder')
    def docs_reorder(self, request, uid=None):
        """
        Bulk update folder_id and order_index for a set of documents.
        @param items: list of {uid, folder_id?, order_index?}
        @return: reorder result
        """
        items = request.data.get('items') or []
        if not isinstance(items, list):
            return Response({'success': False, 'message': 'items must be a list'}, status=status.HTTP_400_BAD_REQUEST)
        result = ClassroomDocService().reorder(classroom_uid=str(uid), items=items)
        return Response(result)

    @action(detail=True, methods=['get', 'post'], url_path='folders')
    def folders(self, request, uid=None):
        """
        List (GET) or create (POST) folders for a classroom.
        @param name: folder name (POST, required)
        @param parent_folder_id: parent folder uid (POST, optional)
        @return: folder tree, or the created folder
        """
        from features.resource.serializers.resource_folder_serializer import (
            ResourceFolderCreateRequestSerializer,
            ResourceFolderResponseSerializer,
            ResourceFolderTreeSerializer,
        )

        folder_service = ClassroomDocService()._folder_service
        classroom_uuid = uuid.UUID(str(uid))

        if request.method == 'POST':
            serializer = ResourceFolderCreateRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            try:
                folder = folder_service.create_folder(
                    classroom_id=classroom_uuid,
                    teacher_id=request.user.uid,
                    name=data['name'],
                    parent_folder_id=data.get('parent_folder_id'),
                    order_index=data.get('order_index', 0),
                    color=data.get('color'),
                    is_preview_only=data.get('is_preview_only', False),
                )
            except ValueError as exc:
                return Response({'success': False, 'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            ClassroomActivityLogService().log(
                classroom_uid=uid,
                log_level='detail',
                event_type='folder_created',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=str(folder.uid),
                target_name=folder.name,
            )
            return Response(ResourceFolderResponseSerializer(folder).data, status=status.HTTP_201_CREATED)

        folders = folder_service.list_tree(classroom_uuid)
        return Response(ResourceFolderTreeSerializer(folders, many=True).data)

    @action(detail=True, methods=['patch', 'delete'], url_path='folders/(?P<folder_uid>[^/.]+)')
    def folder_detail(self, request, uid=None, folder_uid=None):
        """
        Update (PATCH) or delete (DELETE) a folder.
        @return: updated folder, or no content
        """
        from features.resource.serializers.resource_folder_serializer import (
            ResourceFolderResponseSerializer,
            ResourceFolderUpdateRequestSerializer,
        )

        folder_service = ClassroomDocService()._folder_service
        try:
            folder = folder_service.repository.find(folder_uid)
        except Exception as exc:
            return Response({'success': False, 'message': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            folder_service.delete_folder(folder)
            ClassroomActivityLogService().log(
                classroom_uid=uid,
                log_level='major',
                event_type='folder_deleted',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=str(folder.uid),
                target_name=folder.name,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ResourceFolderUpdateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if 'is_preview_only' in data:
            target = bool(data['is_preview_only'])
            if target:
                other = folder_service.repository.get_preview_folder(folder.classroom_id)
                if other and str(other.uid) != str(folder.uid):
                    return Response(
                        {'success': False, 'message': 'Lớp học đã có Preview folder khác.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            folder_service.repository.update(folder, is_preview_only=target)
        if 'name' in data:
            folder_service.rename_folder(folder, data['name'])
        if 'parent_folder_id' in data:
            try:
                folder_service.move_folder(folder, data['parent_folder_id'])
            except ValueError as exc:
                return Response({'success': False, 'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if 'order_index' in data:
            folder_service.repository.update(folder, order_index=int(data['order_index']))
        if 'color' in data:
            folder_service.repository.update(folder, color=data['color'])

        folder = folder_service.repository.find(folder_uid)
        return Response(ResourceFolderResponseSerializer(folder).data)

    def docs_delete(self, request, uid=None, resource_uid=None):
        """
        Delete a document from a classroom.
        @return: no content
        """
        result = ClassroomDocService().delete_doc(
            classroom_uid=str(uid),
            resource_uid=resource_uid,
        )
        if result.get('success'):
            ClassroomActivityLogService().log(
                classroom_uid=uid,
                log_level='detail',
                event_type='document_deleted',
                actor_id=request.user.uid,
                actor_name=getattr(request.user, 'full_name', '') or getattr(request.user, 'username', ''),
                actor_role='teacher',
                target_id=resource_uid,
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['get'], url_path='activity')
    def activity(self, request, uid=None):
        """
        List classroom activity log entries.
        @param level: 'major' or 'detail', default 'major'
        @param limit: max entries, default 50
        @param before: iso datetime cursor
        @return: activity log entries
        """
        from datetime import datetime as dt
        log_level = request.query_params.get('level', 'major')
        limit = min(int(request.query_params.get('limit', 50)), 200)
        before_str = request.query_params.get('before')
        before = None
        if before_str:
            try:
                before = dt.fromisoformat(before_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        logs = ClassroomActivityLogService().list(
            classroom_uid=uid,
            log_level=log_level if log_level in ('major', 'detail') else None,
            limit=limit,
            before=before,
        )
        return Response(logs)
