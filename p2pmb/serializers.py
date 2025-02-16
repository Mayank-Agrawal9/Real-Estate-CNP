from collections import deque
from rest_framework import serializers

from agency.models import Investment
from .models import MLMTree, User, Package


class MLMTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['child', 'children']

    def get_children(self, obj):
        """
        Recursively fetch and serialize child nodes for each parent node.
        """
        children = MLMTree.objects.filter(parent=obj.child)
        return MLMTreeSerializer(children, many=True).data

    def validate(self, data):
        """
        Validate that the child doesn't already exist in the tree.
        """
        child = data.get('child')
        investment = Investment.objects.filter(user=child, package__isnull=False, investment_type='p2pmb').last()
        if not investment:
            raise serializers.ValidationError("First Please buy package then you are able to get into P2PMB model.")
        elif investment and not investment.is_approved:
            raise serializers.ValidationError("Your request is in process, Once it is approved we will notify you.")
        if MLMTree.objects.filter(child=child).exists():
            raise serializers.ValidationError("This child is already assigned to a parent.")
        return data

    def create(self, validated_data):
        child = validated_data['child']
        master_node = self.get_or_create_master_node()
        parent_node = self.find_next_available_parent_node(master_node)
        return self.create_mlm_tree_node(parent_node, child)

    def create_mlm_tree_node(self, parent_node, child_node):
        """
        Create the MLM tree node with parent-child relation.
        """
        position = MLMTree.objects.filter(parent=parent_node.child).count() + 1
        level = parent_node.level + 1
        MLMTree.objects.create(
            parent=parent_node.child,
            child=child_node,
            position=position,
            level=level,
            referral_by=parent_node.child
        )

    def find_next_available_parent_node(self, master_node):
        """
        Find the next available parent node using BFS for a balanced binary tree.
        """
        queue = deque([master_node])

        while queue:
            current_node = queue.popleft()
            if current_node:
                children_count = MLMTree.objects.filter(parent=current_node.child).count()

                if children_count < 5:
                    return current_node
                sub_nodes = MLMTree.objects.filter(parent=current_node.child).order_by('position')
                queue.extend(sub_nodes)

        raise serializers.ValidationError("No available parent node found.")

    def get_or_create_master_node(self):
        """
        Ensures the Master Node exists or creates it if necessary.
        """
        master_node = MLMTree.objects.filter(parent=None).first()
        if not master_node:
            master_user = User.objects.filter(username="Master").first()
            if not master_user:
                raise serializers.ValidationError("Master user must be created before adding MLM tree nodes.")
            master_node = MLMTree.objects.create(
                parent=None, child=master_user, position=1, level=0, referral_by=None)
        return master_node


class MLMTreeNodeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['child', 'position', 'level', 'children']

    def get_children(self, obj):
        children = MLMTree.objects.filter(parent=obj.child).order_by('position')
        return MLMTreeNodeSerializer(children, many=True).data


class PackageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Package
        fields = ['id', 'name', 'description', 'amount']
