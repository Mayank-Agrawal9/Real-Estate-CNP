from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from p2pmb.models import MLMTree
from p2pmb.serializers import MLMTreeSerializer, MLMTreeNodeSerializer


# Create your views here.


class MLMTreeCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Handle the creation of a new child in the MLM tree.

        Validate the input and add the child to the appropriate position.
        """
        serializer = MLMTreeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                mlm_tree = serializer.create(serializer.validated_data)
                return Response(
                    MLMTreeSerializer(mlm_tree).data,
                    status=status.HTTP_201_CREATED
                )
            except serializers.ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )


class MLMTreeView(APIView):
    """
    API to retrieve the MLM tree structure.
    """

    def get(self, request):
        # Find the master node (root of the tree)
        master_node = MLMTree.objects.filter(parent=None).first()
        if not master_node:
            return Response(
                {"detail": "Error"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Serialize the tree starting from the master node
        serializer = MLMTreeNodeSerializer(master_node)
        return Response(serializer.data)