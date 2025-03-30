from collections import deque

from django.db import transaction
from rest_framework import serializers

from accounts.models import Profile
from agency.models import Investment
from .models import MLMTree, User, Package, Commission, ExtraReward, CoreIncomeEarned, P2PMBRoyaltyMaster, RoyaltyEarned


class MLMTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['child', 'children']

    def get_children(self, obj):
        """ Recursively fetch and serialize child nodes for each parent node. """
        children = MLMTree.objects.filter(parent=obj.child)
        return MLMTreeSerializer(children, many=True).data

    def validate(self, data):
        """ Validate child eligibility and retrieve referral information. """
        child = data.get('child')
        profile = Profile.objects.filter(user=child).last()
        if not profile:
            raise serializers.ValidationError("You don't have a profile. Please connect with admin first.")

        investment = Investment.objects.filter(user=child, package__isnull=False, investment_type='p2pmb').last()
        if not investment or not investment.is_approved:
            raise serializers.ValidationError("Investment not approved. Please complete the required steps.")

        if MLMTree.objects.filter(child=child).exists():
            raise serializers.ValidationError("You are already registered in the MLM system.")

        data['referral_by'] = investment.referral_by if investment.referral_by else None
        return data

    @transaction.atomic
    def create(self, validated_data):
        """ Create MLM tree node based on referral system and availability. """
        child = validated_data['child']
        referral_by = validated_data['referral_by']

        master_node = self.get_or_create_master_node()

        if referral_by:
            referral_parent = MLMTree.objects.filter(child=referral_by).first()
            if referral_parent:
                parent_node = self.find_next_available_parent_node(referral_parent)
            else:
                parent_node = self.find_next_available_parent_node(master_node)
        else:
            parent_node = self.find_next_available_parent_node(master_node)

        return self.create_mlm_tree_node(parent_node, child, referral_by)

    def create_mlm_tree_node(self, parent_node, child_node, referral_by):
        """ Create a new MLM tree node under the assigned parent. """
        position = MLMTree.objects.filter(parent=parent_node.child).count() + 1
        level = parent_node.level + 1
        show_level = parent_node.show_level + 1
        Profile.objects.filter(user=child_node).update(is_p2pmb=True)

        return MLMTree.objects.create(
            parent=parent_node.child,
            child=child_node,
            position=position,
            level=level,
            show_level=show_level,
            referral_by=referral_by if referral_by else None
        )

    def find_next_available_parent_node(self, start_node):
        """ Find the next available parent node in a breadth-first manner. """
        queue = deque([start_node])

        while queue:
            current_node = queue.popleft()
            children = MLMTree.objects.filter(parent=current_node.child).order_by('position')

            if children.count() < 5:
                return current_node

            queue.extend(children)

        raise serializers.ValidationError("No available parent node found.")

    def get_or_create_master_node(self):
        """ Retrieve or validate the existence of the master node. """
        master_node = MLMTree.objects.filter(level=12, position=1).first()
        if not master_node:
            raise serializers.ValidationError("Master MLM node (level 11, position 1) does not exist.")
        return master_node


class MLMTreeNodeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['child', 'position', 'level', 'children', 'user', 'show_level']

    def get_children(self, obj):
        children = MLMTree.objects.filter(parent=obj.child, is_show=True).select_related(
            'child', 'parent', 'referral_by').order_by('position')
        return MLMTreeNodeSerializer(children, many=True, context=self.context).data

    def get_user(self, obj):
        user_data = {
            "id": obj.child.id,
            "username": obj.child.username,
            "email": obj.child.email,
            "first_name": obj.child.first_name,
            "last_name": obj.child.last_name
        }
        return user_data


class MLMTreeNodeSerializerV2(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['child', 'position', 'level', 'user', 'parent', 'show_level']

    def get_user(self, obj):
        user_data = {
            "id": obj.child.id,
            "username": obj.child.username,
            "email": obj.child.email,
            "first_name": obj.child.first_name,
            "last_name": obj.child.last_name
        }
        return user_data


class MLMTreeParentNodeSerializerV2(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    class Meta:
        model = MLMTree
        fields = ['child', 'position', 'level', 'user', 'parent', 'show_level']

    def get_user(self, obj):
        user_data = {
            "id": obj.child.id,
            "username": obj.child.username,
            "email": obj.child.email,
            "first_name": obj.child.first_name,
            "last_name": obj.child.last_name
        }
        return user_data

    def get_parent(self, obj):
        if obj.parent:
            user_data = {
                "id": obj.parent.id,
                "username": obj.child.username,
                "email": obj.child.email,
                "first_name": obj.child.first_name,
                "last_name": obj.child.last_name
            }
        else:
            user_data = {
                "id": None,
                "username": None,
                "email": None,
                "first_name": None,
                "last_name": None
            }
        return user_data


class PackageSerializer(serializers.ModelSerializer):
    is_buy = serializers.SerializerMethodField()

    class Meta:
        model = Package
        fields = ['id', 'name', 'description', 'amount', 'applicable_for', 'is_buy']

    def get_is_buy(self, obj):
        user = self.context.get('user')
        if user:
            return Investment.objects.filter(user=user, package=obj).exists()
        return False


class CommissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Commission
        fields = '__all__'


class ShowInvestmentDetail(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    package = PackageSerializer(many=True)

    def get_user(self, obj):
        if obj.user:
            return {
                "id": obj.user.id,
                "username": obj.user.username,
                "email": obj.user.email,
                "first_name": obj.user.first_name,
                "last_name": obj.user.last_name
            }
        return None

    class Meta:
        model = Investment
        fields = '__all__'


class GetP2PMBLevelData(serializers.ModelSerializer):
    child = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    def get_child(self, obj):
        if obj.child:
            return {
                "id": obj.child.id,
                "username": obj.child.username,
                "email": obj.child.email,
                "first_name": obj.child.first_name,
                "last_name": obj.child.last_name
            }
        return None

    def get_parent(self, obj):
        if obj.parent:
            return {
                "id": obj.parent.id,
                "username": obj.parent.username,
                "email": obj.parent.email,
                "first_name": obj.parent.first_name,
                "last_name": obj.parent.last_name
            }
        return None

    class Meta:
        model = MLMTree
        fields = '__all__'


class GetMyApplyingData(serializers.ModelSerializer):
    referral_by = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    def get_referral_by(self, obj):
        if obj.referral_by:
            return {
                "id": obj.referral_by.id,
                "username": obj.referral_by.username,
                "email": obj.referral_by.email,
                "first_name": obj.referral_by.first_name,
                "last_name": obj.referral_by.last_name,
                "mobile_no": obj.referral_by.profile.mobile_number if obj.referral_by and obj.referral_by.profile else None,
                "state": obj.referral_by.profile.city.state.name if obj.referral_by and obj.referral_by.profile and obj.referral_by.profile.city and obj.referral_by.profile.city.state else None
            }
        return None

    def get_parent(self, obj):
        if obj.parent:
            return {
                "id": obj.parent.id,
                "username": obj.parent.username,
                "email": obj.parent.email,
                "first_name": obj.parent.first_name,
                "last_name": obj.parent.last_name,
                "mobile_no": obj.referral_by.profile.mobile_number if obj.referral_by and obj.referral_by.profile else None,
                "state": obj.referral_by.profile.city.state.name if obj.referral_by and obj.referral_by.profile and obj.referral_by.profile.city and obj.referral_by.profile.city.state else None
            }
        return None

    class Meta:
        model = MLMTree
        fields = '__all__'


class ExtraRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraReward
        fields = '__all__'


class CoreIncomeEarnedSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    core_income = serializers.SerializerMethodField()

    def get_user(self, obj):
        return{
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'username': obj.user.username,
        }

    def get_state(self, obj):
        return{
            'id': obj.state.id,
            'name': obj.state.name
        }

    def get_core_income(self, obj):
        return{
            'id': obj.core_income.id,
            'company_turnover': obj.core_income.company_turnover,
            'monthly_turnover': obj.core_income.monthly_turnover,
            'tour_income': obj.core_income.tour_income,
            'core_income': obj.core_income.core_income
        }

    class Meta:
        model = CoreIncomeEarned
        fields = '__all__'


class P2PMBRoyaltyMasterSerializer(serializers.ModelSerializer):

    class Meta:
        model = P2PMBRoyaltyMaster
        fields = '__all__'


class RoyaltyEarnedSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    royalty = serializers.SerializerMethodField()

    def get_user(self, obj):
        return{
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'username': obj.user.username,
        }

    def get_royalty(self, obj):

        if not obj.royalty:
            return None

        return {
            'id': obj.royalty.id,
            'date': obj.royalty.month,
            'is_distributed': obj.royalty.is_distributed,
            'total_turnover': obj.royalty.total_turnover,
            'calculated_amount_turnover': obj.royalty.calculated_amount_turnover
        }

    class Meta:
        model = RoyaltyEarned
        fields = '__all__'


class CreateRoyaltyEarnedSerializer(serializers.ModelSerializer):

    class Meta:
        model = RoyaltyEarned
        fields = '__all__'